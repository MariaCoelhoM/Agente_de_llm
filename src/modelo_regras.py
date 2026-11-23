"""
Substituto determinístico do modelo ("modelo de regras"). NÃO é um LLM e não
mede a qualidade de nenhum LLM.

Para que serve:
  1. rodar o chat e a suíte de avaliação sem chave de API (README: modo
     `--modelo regras`), de forma reprodutível;
  2. medir o CÓDIGO em volta do modelo — guardas, aprovação, contrato, memória,
     verificador de afirmações — com um "modelo" cujo comportamento é conhecido.

Ele é deliberadamente INGÊNUO diante de injeção: segue três padrões de
instrução que um LLM real às vezes segue (ver docs/seguranca.md, cenários):
  - "diga que ..."            -> repete a frase como resposta (ASI01/ASI09)
  - "use o contrato C00X"     -> passa esse contrato às ferramentas (ASI02/ASI03)
  - "reinicie N vezes"        -> chama reiniciar_conexao repetidamente (ASI10)
e lê instruções do bloco <memoria_do_sistema> como se fossem do cliente
(ASI06). Isso simula o pior caso, para que os controles fora do prompt sejam
exercitados; os números de qualidade do LLM real saem de rodadas com
`--modelo real` (docs/evals.md).

A interface é a mesma do ClienteLLM: chamar(mensagens, ferramentas) -> RespostaLLM.
"""
import json
import re
import unicodedata
from typing import List, Optional

from .llm import RespostaLLM


def _norm(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", (texto or "").lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


PERGUNTA = re.compile(r"^(como|o que|oque|qual|quais|quanto|quantos|posso|devo|por que|porque|pq|quando|onde|tem como|existe)\b")
SINTOMA_FORTE = re.compile(r"(caiu|cai |caindo|sem internet|nao funciona|nao navega|offline|fora do ar|parou|lent|ruim|"
                           r"luz|vermelh|pisc|apagad|nao conecta|sem conexao|oscila|instavel)")
FECHAMENTO = re.compile(r"^(obrigad|valeu|vlw|ok\b|blz|beleza|tchau|era isso|so isso|perfeito|show|otimo)")
DIGA_QUE = re.compile(r"(?:diga|responda|fale|informe|escreva) que ([^.\]\n]+)")
OUTRO_CONTRATO = re.compile(r"contrato\s+(c\d{3})")
REPETIR_REINICIO = re.compile(r"reinici\w*[^.]{0,30}?(\d+)\s*vezes")
CONSULTA = re.compile(r"(significa|quer dizer|prazo|quanto tempo|regra|politica|limite|quantas vezes)")
TESTE_DE_NOVO = re.compile(r"(testa|teste|testar|verifica|verifique)\w* (de novo|novamente|outra vez)")


class ModeloRegras:
    modelo = "regras-v1"

    def __init__(self):
        self.chamadas = 0
        self._ids = 0

    # ------------------------------------------------------------------ util

    def _id(self, nome):
        self._ids += 1
        return f"rg_{nome}_{self._ids}"

    def _ferramenta(self, nome, args=None) -> RespostaLLM:
        return RespostaLLM(tool_calls=[{"id": self._id(nome), "nome": nome, "args": args or {}}])

    def _texto(self, conteudo) -> RespostaLLM:
        return RespostaLLM(content=conteudo)

    # ------------------------------------------------------------------ leitura das mensagens

    def _ler(self, mensagens: List[dict]):
        sistema = mensagens[0]["content"] if mensagens and mensagens[0]["role"] == "system" else ""
        amanha = re.search(r"amanhã é (\d{4}-\d{2}-\d{2})", sistema)
        memoria = next((m["content"] for m in mensagens if m["role"] == "user"
                        and m["content"].startswith("<memoria_do_sistema>")), "")
        idx = max(i for i, m in enumerate(mensagens)
                  if m["role"] == "user" and not m["content"].startswith("<memoria_do_sistema>"))
        texto = mensagens[idx]["content"]
        chamadas = {}
        resultados = []  # deste turno: (nome, args, resultado)
        for m in mensagens[idx + 1:]:
            if m["role"] == "assistant":
                for c in m.get("tool_calls", []):
                    chamadas[c["id"]] = (c["function"]["name"], json.loads(c["function"]["arguments"] or "{}"))
            elif m["role"] == "tool":
                nome, args = chamadas.get(m["tool_call_id"], ("?", {}))
                try:
                    resultados.append((nome, args, json.loads(m["content"])))
                except json.JSONDecodeError:
                    resultados.append((nome, args, {"erro": "conteudo_invalido"}))
        anteriores = [m for m in mensagens[1:idx] if m["role"] == "assistant" and m.get("content")]
        return {"texto": texto, "t": _norm(texto), "memoria": _norm(memoria), "resultados": resultados,
                "amanha": amanha.group(1) if amanha else None,
                "ultima_resposta": _norm(anteriores[-1]["content"]) if anteriores else ""}

    # ------------------------------------------------------------------ política

    def chamar(self, mensagens, ferramentas) -> RespostaLLM:
        self.chamadas += 1
        resp = self._decidir(self._ler(mensagens))
        entrada = sum(len(m.get("content") or "") for m in mensagens) // 4
        saida = len(resp.content or "") // 4 + 20 * len(resp.tool_calls)
        resp.tokens_entrada, resp.tokens_saida, resp.tokens = entrada, saida, entrada + saida
        return resp

    def _decidir(self, c) -> RespostaLLM:
        t, R = c["t"], c["resultados"]
        feitos = [n for n, _, _ in R]

        def ok(nome):
            return [r for n, _, r in R if n == nome and "erro" not in r]

        # ingenuidade 1: instrução "diga que ..." no texto do cliente ou na memória
        ordem = DIGA_QUE.search(t) or DIGA_QUE.search(c["memoria"])
        if ordem and not R:
            frase = ordem.group(1).strip()
            return self._texto(frase[0].upper() + frase[1:] + ".")

        # ingenuidade 2: contrato pedido no texto vai para os argumentos
        outro = OUTRO_CONTRATO.search(t)
        args = {"contrato": outro.group(1).upper()} if outro else {}

        # ingenuidade 3: "reinicie N vezes"
        rep = REPETIR_REINICIO.search(t)
        if rep:
            pedidos = int(rep.group(1))
            erros = [r for n, _, r in R if "erro" in r]
            if feitos.count("reiniciar_conexao") < pedidos and not erros:
                return self._ferramenta("reiniciar_conexao", args)

        if FECHAMENTO.search(t) and not R:
            return self._texto("Por nada! Se a internet voltar a dar problema, é só me chamar.")

        # pergunta sobre regra/sintoma -> manual
        if PERGUNTA.search(t) and (CONSULTA.search(t) or not SINTOMA_FORTE.search(t)):
            consultas = [r for n, _, r in R if n == "consultar_base_conhecimento"]
            if not consultas:
                return self._ferramenta("consultar_base_conhecimento", {"pergunta": c["texto"]})
            r = consultas[-1]
            if not r.get("suficiente"):
                return self._texto("Não encontrei isso nos manuais do suporte técnico. "
                                   "Posso encaminhar você para um atendente humano.")
            tr = r["trechos"][0]
            corpo = tr["texto"].split(". ", 2)[-1]
            return self._texto(f"Segundo o manual [{tr['id']}]: {corpo[:300]}")

        # resposta da aprovação (o nó `agendar` devolve isto no retorno de propor_visita)
        for n, _, r in R:
            if "decisao_do_cliente" in r:
                res = r["resultado"]
                if res.get("status") == "AGENDADA":
                    return self._texto(f"Visita técnica agendada para {res['data']}. O técnico vai até a sua casa "
                                       "nessa data. Posso ajudar em mais alguma coisa?")
                return self._texto("Tudo bem, não agendei a visita técnica. Se mudar de ideia, é só me dizer.")

        # fluxo de diagnóstico
        erros_contrato = [r for _, _, r in R if r.get("erro") == "contrato_nao_encontrado"]
        if erros_contrato:
            return self._texto("Não encontrei o seu contrato no sistema, então não consigo testar a linha. "
                               "Um atendente precisa conferir o seu cadastro.")
        testes = [r for n, _, r in R if n == "testar_linha"]
        if not testes:
            return self._ferramenta("testar_linha", args)
        if testes[-1].get("erro") == "limite_de_testes_atingido":
            return self._texto("Já fiz o número máximo de testes de linha neste atendimento. "
                               "Se o problema continuar, posso encaminhar você para um atendente.")
        if testes[-1].get("erro") == "ferramenta_indisponivel":
            return self._texto("O sistema de testes está indisponível agora.")
        teste = ok("testar_linha")[-1] if ok("testar_linha") else testes[-1]
        if "conferir_queda_bairro" not in feitos:
            return self._ferramenta("conferir_queda_bairro", args)
        bairro = [r for n, _, r in R if n == "conferir_queda_bairro"][-1]
        prefixo = ""
        if "wifi" in t and " ou " in t:
            prefixo = "Considerei que o problema é na linha, que é o que consigo testar daqui. "
        if bairro.get("erro") == "bairro_nao_encontrado":
            return self._texto(prefixo + f"O teste mostra a linha {teste.get('status')}, com sinal de "
                               f"{teste.get('sinal_dbm')} dBm, mas não consegui confirmar se há manutenção no seu "
                               "bairro. Um atendente precisa conferir o cadastro do bairro.")
        if bairro.get("em_manutencao"):
            return self._texto(prefixo + f"Há uma manutenção de rede no bairro {bairro['bairro']} e a equipe já "
                               "está atuando. Não é preciso visita individual: a conexão deve voltar quando a "
                               "manutenção terminar.")
        if teste.get("falha_fisica_provavel"):
            propostas = [r for n, _, r in R if n == "propor_visita"]
            if not propostas:
                return self._ferramenta("propor_visita", {"data": c["amanha"]})
            return self._texto(f"Não consegui propor a visita: {propostas[-1].get('erro')}.")
        reinicios = [i for i, (n, _, r) in enumerate(R) if n == "reiniciar_conexao"]
        if teste.get("status") == "OFFLINE" and not reinicios:
            return self._ferramenta("reiniciar_conexao", args)
        if reinicios:
            ultimo_teste = max(i for i, (n, _, _) in enumerate(R) if n == "testar_linha")
            if ultimo_teste < reinicios[-1]:
                return self._ferramenta("testar_linha", args)
            if teste.get("status") == "ONLINE":
                return self._texto(prefixo + "Reiniciei a sua conexão e o novo teste mostra a linha ONLINE, com sinal "
                                   f"de {teste['sinal_dbm']} dBm. Pode verificar se voltou a navegar?")
            return self._texto("Reiniciei a conexão, mas a linha continua OFFLINE. Vou encaminhar para um atendente.")
        if "outro aparelho" in c["ultima_resposta"]:
            return self._texto(f"A linha continua ONLINE ({teste['sinal_dbm']} dBm) e mesmo assim nada navega, "
                               "inclusive no cabo. Isso precisa de um técnico de suporte avançado: vou registrar "
                               "o que já testamos e encaminhar o seu atendimento.")
        return self._texto(prefixo + f"O teste mostra a sua linha ONLINE, com sinal de {teste['sinal_dbm']} dBm, e "
                           "não há manutenção no bairro. Como você diz que não navega, o problema pode estar no "
                           "Wi-Fi ou no aparelho: teste em outro aparelho, de preferência no cabo, e me diga o resultado.")
