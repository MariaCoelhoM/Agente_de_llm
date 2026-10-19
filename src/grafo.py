import json
import re
import time
from typing import Optional

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import ValidationError

from . import config, guardas, memoria, rag, tools
from .estado import EstadoAtendimento
from .llm import ErroLLMFatal
from .schemas import Fonte, RespostaAtendimento

DECISOES = {"aprovar", "rejeitar", "editar", "expirou"}
FERRAMENTAS_COM_CONTRATO = {"testar_linha", "conferir_queda_bairro", "reiniciar_conexao"}
PADRAO_CITACAO = re.compile(r"\b([A-Z]\d{2})\b")
PADRAO_HUMANO = re.compile(
    r"\b(fatura|boleto|cobranc\w*|desconto|segunda via|cancel\w+|pagamento|reembolso|"
    r"falar com (um |uma )?(atendente|pessoa|humano))\b"
)

PADRAO_SINTOMA = re.compile(
    r"\b(internet|wi-?fi|net|sinal|luz|luzes|led|modem|roteador|router|caiu|caindo|cai|lent\w*|"
    r"trav\w*|conexao|rede|fibra|cabo|offline|navega\w*|site|sites|video|videos|chamada|ping|"
    r"velocidade|oscila\w*|instavel|queda|vermelh\w*|pisc\w*|laranja|verde|apagad\w*|"
    r"tecnico|visita|equipamento|aparelho|aparelhos|celular|notebook|tv)\b"
)
TEXTO_PEDIR_DETALHES = (
    "Não consegui entender qual é o problema. Para eu poder ajudar, me conte: o que a luz do modem mostra "
    "(verde, vermelha, piscando ou apagada) e se a falha acontece em todos os aparelhos ou só em um."
)

TEXTOS_HUMANO = {
    "encaminhado_humano": "Esse assunto (cobrança, fatura, cancelamento ou pedido de atendente) não é do suporte técnico. Aqui eu testo a linha, confiro queda no bairro, reinicio a conexão e proponho visita técnica. Vou encaminhar você para um atendente humano.",
    "aprovacao_expirada": "Não recebi sua resposta sobre a visita técnica a tempo, então nada foi agendado. Vou encaminhar você para um atendente humano.",
}
TEXTO_HUMANO_PADRAO = "Não consegui concluir seu atendimento por aqui. Vou encaminhar você para um atendente humano, com o que já foi verificado."
TEXTO_FORA_DO_CORPUS = "Não encontrei essa informação nos manuais do suporte técnico. Posso encaminhar você para um atendente humano."


def _sem_acento_minusculo(texto: str) -> str:
    return rag._sem_acento(texto.lower())


def _carregar_prompt(nome: str) -> str:
    import os

    with open(os.path.join(config.PASTA_PROMPTS, nome), encoding="utf-8") as arquivo:
        return arquivo.read().strip()


def _ferramentas_ok(trajetoria, nome):
    return [t for t in trajetoria if t.get("tipo") == "ferramenta" and t["nome"] == nome
            and "erro" not in t["resultado"]]


def construir_grafo(llm, checkpointer=None, indice: Optional[rag.Indice] = None):
    def entrada(estado):
        hoje = tools._hoje().isoformat()
        if not (estado.get("mensagem") or "").strip():
            return {"hoje": hoje, "motivo_parada": "encaminhado_humano", "mensagens": [],
                    "trajetoria": [{"tipo": "entrada_vazia"}]}
        return {
            "hoje": hoje,
            "voltas": 0, "passos_ferramenta": 0,
            "visita_proposta": None, "decisao_humana": None, "motivo_parada": None,
            "mensagens": [{"role": "user", "content": estado["mensagem"]}],
        }

    def carregar_memoria(estado):
        memoria.aplicar_decaimento(estado["hoje"])
        contexto = memoria.montar_contexto(estado["contrato"], estado["mensagem"], estado["hoje"])
        return {"memoria_contexto": contexto,
                "trajetoria": [{"tipo": "memoria", "carregada": bool(contexto)}]}

    def triagem(estado):
        texto = _sem_acento_minusculo(estado["mensagem"])
        if PADRAO_HUMANO.search(texto):
            return {"rota": "humano", "motivo_parada": "encaminhado_humano",
                    "trajetoria": [{"tipo": "triagem", "rota": "humano", "regra": "palavra_chave"}]}
        if not PADRAO_SINTOMA.search(texto):
            return {"rota": "incompleta", "motivo_parada": "entrada_incompleta",
                    "resposta_texto": TEXTO_PEDIR_DETALHES,
                    "trajetoria": [{"tipo": "triagem", "rota": "incompleta", "regra": "sem_palavra_de_sintoma"}]}
        return {"rota": "suporte", "trajetoria": [{"tipo": "triagem", "rota": "suporte"}]}

    def _mensagens_para_o_modelo(estado):
        sistema = _carregar_prompt(config.PROMPT_SISTEMA)
        sistema += f"\n\nContrato da sessão: {estado['contrato']}. Hoje é {estado['hoje']}."
        sistema += "\n\n" + memoria.carregar_procedural()
        if estado.get("memoria_contexto"):
            sistema += "\n\n" + estado["memoria_contexto"]
        return [{"role": "system", "content": sistema}] + estado["mensagens"]

    def agente(estado):
        motivo = guardas.verificar_orcamento(estado)
        if motivo:
            return {"motivo_parada": motivo, "trajetoria": [{"tipo": "orcamento", "motivo": motivo}]}
        inicio = time.monotonic()
        try:
            resp = llm.chamar(_mensagens_para_o_modelo(estado), tools.FERRAMENTAS_OPENAI)
        except ErroLLMFatal as erro:
            return {"motivo_parada": "erro_fatal_llm",
                    "trajetoria": [{"tipo": "erro_llm", "detalhe": str(erro)}]}
        saida = {
            "voltas": estado.get("voltas", 0) + 1,
            "mensagens": [resp.mensagem],
            "tokens": resp.tokens,
            "segundos_ativos": time.monotonic() - inicio,
        }
        if not resp.tool_calls:
            saida["motivo_parada"] = "resposta_final"
            saida["resposta_texto"] = resp.content or ""
            saida["trajetoria"] = [{"tipo": "resposta_final", "conteudo": resp.content}]
        return saida

    def ferramentas(estado):
        ultima = estado["mensagens"][-1]
        trajetoria_local = list(estado.get("trajetoria", []))
        novos_msgs, novos_traj = [], []
        passos = estado.get("passos_ferramenta", 0)
        motivo, proposta = None, None

        def registrar(chamada_id, nome, args, resultado, **extra):
            item = {"tipo": "ferramenta", "nome": nome, "args": args, "resultado": resultado, **extra}
            novos_traj.append(item)
            trajetoria_local.append(item)
            if chamada_id:
                novos_msgs.append({"role": "tool", "tool_call_id": chamada_id,
                                   "content": json.dumps(resultado, ensure_ascii=False)})

        for c in ultima.get("tool_calls", []):
            cid, nome = c["id"], c["function"]["name"]
            try:
                args = json.loads(c["function"]["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {}
            extra = {}
            if nome in FERRAMENTAS_COM_CONTRATO:
                if args.get("contrato") not in (None, estado["contrato"]):
                    extra["contrato_sobrescrito"] = args["contrato"]
                args = {"contrato": estado["contrato"]}
            if motivo or proposta:
                registrar(cid, nome, args, {"erro": "ignorada", "motivo": motivo or "aguardando_aprovacao"})
                continue
            if passos >= config.MAX_PASSOS_FERRAMENTA:
                motivo = "limite_de_ferramentas"
                registrar(cid, nome, args, {"erro": motivo})
                continue
            if guardas.detectar_laco(trajetoria_local, nome, args):
                motivo = "laco_detectado"
                registrar(cid, nome, args, {"erro": motivo})
                continue
            passos += 1
            if nome == "testar_linha":
                feitos = [t for t in trajetoria_local if t.get("tipo") == "ferramenta"
                          and t["nome"] == "testar_linha"
                          and t["resultado"].get("erro") != "limite_de_testes_atingido"]
                if len(feitos) >= config.MAX_TESTES_LINHA:
                    registrar(cid, nome, args, {"erro": "limite_de_testes_atingido",
                                                "maximo": config.MAX_TESTES_LINHA}, **extra)
                    continue
            if nome == "propor_visita":
                resultado = _validar_proposta(estado, trajetoria_local, args)
                registrar(None, nome, args, resultado, **extra) if "proposta" in resultado else \
                    registrar(cid, nome, args, resultado, **extra)
                if "proposta" in resultado:
                    proposta = {"contrato": estado["contrato"], "data": resultado["data"],
                                "tool_call_id": cid,
                                "chave": tools.chave_visita(estado["contrato"], resultado["data"])}
                continue
            funcao = tools.FUNCOES.get(nome)
            if funcao is None:
                registrar(cid, nome, args, {"erro": "ferramenta_desconhecida", "nome": nome}, **extra)
                continue
            try:
                resultado = funcao(**args)
            except TypeError:
                resultado = {"erro": "argumentos_invalidos", "recebido": args}
            registrar(cid, nome, args, resultado, **extra)

        saida = {"mensagens": novos_msgs, "trajetoria": novos_traj, "passos_ferramenta": passos}
        if motivo:
            saida["motivo_parada"] = motivo
        if proposta:
            saida["visita_proposta"] = proposta
        return saida

    def _validar_proposta(estado, trajetoria_local, args):
        data = args.get("data", "")
        if any(t.get("tipo") == "aprovacao_humana" and t["decisao"] in ("rejeitar", "expirou")
               for t in trajetoria_local):
            return {"erro": "cliente_ja_recusou_a_visita"}
        testes = _ferramentas_ok(trajetoria_local, "testar_linha")
        if not testes:
            return {"erro": "teste_de_linha_necessario_antes_de_propor"}
        if not (testes[-1]["resultado"]["falha_fisica_provavel"]
                or testes[-1]["resultado"]["status"] == "OFFLINE"):
            return {"erro": "linha_ok_visita_nao_se_justifica"}
        return tools.propor_visita(estado["contrato"], data)

    def aprovacao(estado):
        vp = estado["visita_proposta"]
        hoje = estado["hoje"]
        resposta = interrupt({
            "acao": "agendar_visita_tecnico",
            "contrato": vp["contrato"],
            "data_proposta": vp["data"],
            "consequencia": "desloca um técnico até a casa do cliente; tem custo e não é desfeito sozinho",
            "opcoes": ["aprovar", "rejeitar", "editar"],
            "janela_edicao": [hoje, _somar_dias(hoje, config.DIAS_MAXIMOS_VISITA)],
            "prazo_segundos": config.PRAZO_APROVACAO_SEGUNDOS,
        })
        if isinstance(resposta, str):
            resposta = {"decisao": resposta}
        decisao = resposta.get("decisao") if isinstance(resposta, dict) else None
        if decisao not in DECISOES:
            decisao, resposta = "rejeitar", {"motivo": "resposta_invalida"}
        data, motivo = vp["data"], resposta.get("motivo")
        if decisao == "editar":
            problema = guardas.validar_data_edicao(resposta.get("data"), hoje)
            if problema:
                decisao, motivo = "rejeitar", f"edicao_invalida:{problema}"
            else:
                data = resposta["data"]
        return {"decisao_humana": {"decisao": decisao, "data": data, "motivo": motivo}}

    def agendar(estado):
        vp, dec = estado["visita_proposta"], estado["decisao_humana"]
        if dec["decisao"] in ("aprovar", "editar"):
            resultado = tools.FUNCOES_INTERNAS["agendar_visita_tecnico"](vp["contrato"], dec["data"], True)
        else:
            resultado = {"agendado": False, "motivo": dec["motivo"] or dec["decisao"]}
        para_o_modelo = {"decisao_do_cliente": dec["decisao"], "resultado": resultado}
        saida = {
            "visita_proposta": None,
            "mensagens": [{"role": "tool", "tool_call_id": vp["tool_call_id"],
                           "content": json.dumps(para_o_modelo, ensure_ascii=False)}],
            "trajetoria": [{"tipo": "aprovacao_humana", "decisao": dec["decisao"],
                            "data_proposta": vp["data"], "data_final": dec["data"],
                            "motivo": dec["motivo"], "resultado": resultado}],
        }
        if dec["decisao"] == "expirou":
            saida["motivo_parada"] = "aprovacao_expirada"
        return saida

    def encaminhar_humano(estado):
        motivo = estado.get("motivo_parada") or "encaminhado_humano"
        return {"motivo_parada": motivo,
                "resposta_texto": TEXTOS_HUMANO.get(motivo, TEXTO_HUMANO_PADRAO),
                "trajetoria": [{"tipo": "transbordo", "motivo": motivo}]}

    def finalizar(estado):
        trajetoria = estado.get("trajetoria", [])
        motivo = estado.get("motivo_parada") or "resposta_final"
        texto = estado.get("resposta_texto") or TEXTO_HUMANO_PADRAO
        fontes = [Fonte(tipo="ferramenta", id=n) for n in
                  sorted({t["nome"] for t in trajetoria if t.get("tipo") == "ferramenta"
                          and "erro" not in t["resultado"] and t["nome"] != "consultar_base_conhecimento"})]
        if any(t.get("tipo") == "aprovacao_humana" and "erro" not in t["resultado"]
               and t["decisao"] in ("aprovar", "editar") for t in trajetoria):
            fontes.append(Fonte(tipo="ferramenta", id="agendar_visita_tecnico"))
        consultas = [t for t in trajetoria if t.get("tipo") == "ferramenta"
                     and t["nome"] == "consultar_base_conhecimento"]
        recuperados = {tr["id"]: tr for t in consultas if t["resultado"].get("suficiente")
                       for tr in t["resultado"]["trechos"]}
        citados = list(dict.fromkeys(PADRAO_CITACAO.findall(texto)))
        validas = [i for i in citados if i in recuperados]
        invalidas = [i for i in citados if i not in recuperados]
        fontes += [Fonte(tipo="corpus", id=i, detalhe=recuperados[i]["doc"]) for i in validas]

        suficiente, motivo_insuf, encaminhar = True, None, False
        if motivo == "entrada_incompleta":
            suficiente, motivo_insuf, encaminhar = False, motivo, False
        elif motivo != "resposta_final":
            suficiente, motivo_insuf, encaminhar = False, motivo, True
        elif consultas and not recuperados and not fontes:
            suficiente, motivo_insuf, encaminhar = False, "fora_do_corpus", True
            texto = TEXTO_FORA_DO_CORPUS
        elif not fontes:
            suficiente, motivo_insuf = False, "citacao_nao_verificada" if invalidas else "sem_fonte"
        try:
            saida = RespostaAtendimento(
                resultado=texto, fontes=fontes, suficiente=suficiente,
                motivo_insuficiencia=motivo_insuf, encaminhar_humano=encaminhar,
                motivo_parada=motivo, citacoes_invalidas=invalidas,
            ).model_dump()
        except ValidationError as erro:
            saida = RespostaAtendimento(
                resultado=TEXTO_HUMANO_PADRAO, fontes=[], suficiente=False,
                motivo_insuficiencia="saida_invalida", encaminhar_humano=True,
                motivo_parada=motivo,
            ).model_dump()
            saida["erro_validacao"] = str(erro)[:300]
        return {"saida": saida}

    def registrar_memoria(estado):
        trajetoria = estado.get("trajetoria", [])
        if any(t.get("tipo") == "ferramenta" and t["resultado"].get("erro") == "contrato_nao_encontrado"
               for t in trajetoria):
            return {"trajetoria": [{"tipo": "memoria_gravada", "gravou": False, "motivo": "contrato_inexistente"}]}
        escrito = memoria.gravar_atendimento(estado["contrato"], estado["hoje"],
                                             estado["mensagem"], trajetoria)
        return {"trajetoria": [{"tipo": "memoria_gravada", "gravou": True, "resultado": escrito}]}

    def apos_entrada(estado):
        return "encaminhar_humano" if estado.get("motivo_parada") else "carregar_memoria"

    def apos_triagem(estado):
        return {"humano": "encaminhar_humano", "incompleta": "finalizar"}.get(estado["rota"], "agente")

    def apos_agente(estado):
        motivo = estado.get("motivo_parada")
        if motivo == "resposta_final":
            return "finalizar"
        if motivo:
            return "encaminhar_humano"
        return "ferramentas"

    def apos_ferramentas(estado):
        if estado.get("visita_proposta"):
            return "aprovacao"
        if estado.get("motivo_parada"):
            return "encaminhar_humano"
        return "agente"

    def apos_agendar(estado):
        return "encaminhar_humano" if estado.get("motivo_parada") == "aprovacao_expirada" else "agente"

    g = StateGraph(EstadoAtendimento)
    for nome, fn in [("entrada", entrada), ("carregar_memoria", carregar_memoria), ("triagem", triagem),
                     ("agente", agente), ("ferramentas", ferramentas), ("aprovacao", aprovacao),
                     ("agendar", agendar), ("encaminhar_humano", encaminhar_humano),
                     ("finalizar", finalizar), ("registrar_memoria", registrar_memoria)]:
        g.add_node(nome, fn)
    g.add_edge(START, "entrada")
    g.add_conditional_edges("entrada", apos_entrada, ["carregar_memoria", "encaminhar_humano"])
    g.add_edge("carregar_memoria", "triagem")
    g.add_conditional_edges("triagem", apos_triagem, ["agente", "encaminhar_humano", "finalizar"])
    g.add_conditional_edges("agente", apos_agente, ["ferramentas", "finalizar", "encaminhar_humano"])
    g.add_conditional_edges("ferramentas", apos_ferramentas, ["aprovacao", "agente", "encaminhar_humano"])
    g.add_edge("aprovacao", "agendar")
    g.add_conditional_edges("agendar", apos_agendar, ["agente", "encaminhar_humano"])
    g.add_edge("encaminhar_humano", "finalizar")
    g.add_edge("finalizar", "registrar_memoria")
    g.add_edge("registrar_memoria", END)
    return g.compile(checkpointer=checkpointer)


def _somar_dias(iso: str, dias: int) -> str:
    import datetime

    return (datetime.date.fromisoformat(iso) + datetime.timedelta(days=dias)).isoformat()


_grafos = {}


def obter_grafo(llm, checkpointer=None, indice: Optional[rag.Indice] = None):

    chave = (id(llm), id(checkpointer), id(indice))
    if chave not in _grafos:
        _grafos[chave] = (llm, checkpointer, indice, construir_grafo(llm, checkpointer, indice))
    return _grafos[chave][3]
