"""
O chatbot (Parte 3): uma conversa de vários turnos com o cliente, sobre o mesmo
grafo da Parte 2.

  python -m src.chat --telefone +5511900000004             # modelo real (.env)
  python -m src.chat --telefone +5511900000004 --modelo regras   # sem chave de API

Cada mensagem do cliente é um TURNO: uma invocação do grafo sobre o mesmo
thread_id, e portanto sobre o mesmo checkpoint. Quando o grafo propõe uma
visita, ele pausa (interrupt) e a próxima mensagem do cliente é lida PELO
CÓDIGO como resposta à aprovação: "sim", "não" ou uma data. O modelo não
interpreta essa resposta e não consegue aprová-la por conta própria.

A identidade vem do canal (controle C1, docs/seguranca.md): o contrato é o
vinculado ao telefone que abriu a conversa, e nada do que se digita o troca.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import threading
import uuid
from typing import Callable, List, Optional

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.errors import GraphRecursionError
from langgraph.types import Command

from . import config, db, memoria, tools
from . import observabilidade as obs
from .grafo import obter_grafo
from .llm import ClienteLLM


LIMITE_ENTRADA = 500


class SessaoRecusada(Exception):
    """Telefone sem cadastro: a conversa não abre (fail-closed)."""


def _commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, cwd=config.RAIZ, timeout=5).stdout.strip() or "sem-git"
    except Exception:
        return "sem-git"


def prompts_em_uso() -> dict:
    usados = {}
    for papel, nome in (("sistema", config.PROMPT_SISTEMA), ("procedural", config.PROMPT_PROCEDURAL)):
        with open(os.path.join(config.PASTA_PROMPTS, nome), "rb") as arquivo:
            usados[papel] = {"arquivo": nome, "sha256": hashlib.sha256(arquivo.read()).hexdigest()[:12]}
    return usados


def resolver_contrato(telefone: Optional[str], contrato_digitado: Optional[str] = None) -> dict:
    """Controle C1. Com o controle ligado, o contrato vem SÓ do telefone do canal;
    um contrato digitado é ignorado e registrado. Com o controle desligado (só a
    suíte faz isso, para medir a versão anterior), vale o contrato digitado, como
    na Parte 2, em que o contrato era um argumento da linha de comando."""
    if not config.CONTROLES.get("identidade_pelo_canal", True):
        contrato = contrato_digitado or (db.contrato_do_telefone(telefone) if telefone else None)
        if not contrato:
            raise SessaoRecusada("sem contrato")
        return {"contrato": contrato, "origem": "digitado" if contrato_digitado else "canal"}
    contrato = db.contrato_do_telefone(telefone) if telefone else None
    if not contrato:
        raise SessaoRecusada("telefone_sem_cadastro")
    saida = {"contrato": contrato, "origem": "canal"}
    if contrato_digitado and contrato_digitado != contrato:
        saida["contrato_digitado_ignorado"] = contrato_digitado
    return saida


# ----------------------------------------------------------------- aprovação

_SIM = re.compile(r"^\s*(sim|s|pode|ok|okay|aprovo|confirmo|confirmado|claro|isso|beleza|fechado|combinado"
                  r"|quero|aceito|manda|perfeito|certo|t[aá] bom|pode ser)\b", re.IGNORECASE)
_NAO = re.compile(r"\b(n[aã]o|nao quero|rejeito|recuso|cancela|cancelar|melhor n[aã]o|dispenso|nem pensar)\b",
                  re.IGNORECASE)


def interpretar_aprovacao(texto: str, hoje: str) -> Optional[dict]:
    """Lê, por regra, a resposta do cliente à pausa de aprovação. Devolve
    {"decisao": "aprovar" | "rejeitar" | "editar", "data"?} ou None quando não
    entende (o chat pergunta de novo). Uma data no texto vale como edição:
    "não, prefiro dia 22" é editar para o dia 22. Quem valida a data (formato e
    janela) é o nó `aprovacao`, não esta função."""
    texto = (texto or "").strip()
    base = datetime.date.fromisoformat(hoje)
    m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", texto)
    if m:
        return {"decisao": "editar", "data": m.group(1)}
    m = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", texto)
    if m:
        dia, mes = int(m.group(1)), int(m.group(2))
        ano = int(m.group(3)) if m.group(3) else base.year
        ano = ano + 2000 if ano < 100 else ano
        try:
            alvo = datetime.date(ano, mes, dia)
            if not m.group(3) and alvo < base:
                alvo = datetime.date(ano + 1, mes, dia)
            return {"decisao": "editar", "data": alvo.isoformat()}
        except ValueError:
            return {"decisao": "editar", "data": "invalida"}
    m = re.search(r"\bdia (\d{1,2})\b", texto, re.IGNORECASE)
    if m:
        dia = int(m.group(1))
        ano, mes = base.year, base.month
        if dia < base.day:
            ano, mes = (ano + 1, 1) if mes == 12 else (ano, mes + 1)
        try:
            return {"decisao": "editar", "data": datetime.date(ano, mes, dia).isoformat()}
        except ValueError:
            return {"decisao": "editar", "data": "invalida"}
    if re.search(r"depois de amanh", texto, re.IGNORECASE):
        return {"decisao": "editar", "data": (base + datetime.timedelta(days=2)).isoformat()}
    if _NAO.search(texto):
        return {"decisao": "rejeitar"}
    if _SIM.search(texto):
        return {"decisao": "aprovar"}
    return None


def cartao_aprovacao(payload: dict) -> str:
    """O que a pessoa vê na pausa (enunciado P2 §8.2): a ação exata, com os
    argumentos e a consequência. Montado pelo código a partir do estado, não
    pelo modelo."""
    de, ate = payload["janela_edicao"]
    return (
        "Para resolver, preciso da sua autorização para uma visita técnica.\n"
        f"  Ação: agendar visita técnica · contrato {payload['contrato']} · data {payload['data_proposta']}\n"
        f"  Consequência: {payload['consequencia']}\n"
        f"Responda \"sim\" para aprovar, \"não\" para recusar, ou diga outra data (de {de} até {ate}).\n"
        f"Prazo para responder: {payload['prazo_segundos'] // 60} min."
    )


# ----------------------------------------------------------------- a conversa

class Conversa:
    """Uma conversa = um atendimento = um thread_id. Usada pelo chat de
    terminal, por `executar_atendimento` (scripts e testes) e pela suíte de
    avaliação: os três passam pelo mesmo caminho."""

    def __init__(self, telefone: Optional[str] = None, contrato: Optional[str] = None, llm=None,
                 checkpointer=None, pasta_logs: Optional[str] = None, rotulo: Optional[str] = None,
                 contrato_digitado: Optional[str] = None):
        if contrato is not None:
            # Entrada de confiança (scripts e testes da Parte 2): o contrato vem
            # do backend, não do cliente. O chat do cliente nunca usa este caminho.
            self.identidade = {"contrato": contrato, "origem": "backend"}
        else:
            self.identidade = resolver_contrato(telefone, contrato_digitado)
        self.contrato = self.identidade["contrato"]
        self.telefone = telefone
        self.llm = llm or ClienteLLM()
        self._conexao = None
        if checkpointer is None:
            os.makedirs(os.path.dirname(config.CAMINHO_CHECKPOINTS), exist_ok=True)
            self._conexao = sqlite3.connect(config.CAMINHO_CHECKPOINTS, check_same_thread=False)
            checkpointer = SqliteSaver(self._conexao)
        self.grafo = obter_grafo(self.llm, checkpointer)
        self.thread_id = f"{self.contrato}:{uuid.uuid4().hex[:8]}"
        self.cfg = {"configurable": {"thread_id": self.thread_id}, "recursion_limit": config.RECURSION_LIMIT}
        self.pasta_logs = pasta_logs or config.PASTA_LOGS
        self.rotulo = rotulo or f"conversa_{self.thread_id.replace(':', '_')}"
        self.pendente: Optional[dict] = None       # payload do interrupt em aberto
        self.tentativas_aprovacao = 0
        self.turnos: List[dict] = []
        self.pausas: List[dict] = []
        self.encerrada = False
        self.erro: Optional[str] = None

    # -- API pública ---------------------------------------------------------

    def enviar(self, texto: str) -> dict:
        """Uma mensagem do cliente. Se há aprovação pendente, a mensagem é a
        resposta a ela; senão, é um turno novo."""
        if self.encerrada:
            return {"tipo": "encerrada", "texto": "Esta conversa já foi transferida para um atendente humano."}
        if self.pendente:
            return self._responder_aprovacao(texto)
        return self._invocar({"thread_id": self.thread_id, "contrato": self.contrato, "mensagem": texto},
                             texto, novo_turno=True)

    def decidir(self, resposta: dict) -> dict:
        """Retoma a pausa com uma decisão já estruturada (scripts e testes)."""
        self.pausas.append({"payload": self.pendente, "resposta": resposta})
        self.pendente, self.tentativas_aprovacao = None, 0
        return self._invocar(Command(resume=resposta), f"[aprovação] {resposta}", novo_turno=False)

    def expirar(self) -> dict:
        return self.decidir({"decisao": "expirou"})

    def fechar(self):
        if self._conexao:
            self._conexao.close()
            self._conexao = None
        obs.descarregar()

    # -- interno -------------------------------------------------------------

    def _responder_aprovacao(self, texto: str) -> dict:
        hoje = self.pendente["janela_edicao"][0]
        resposta = interpretar_aprovacao(texto, hoje)
        if resposta is None:
            self.tentativas_aprovacao += 1
            self.turnos.append({"cliente": memoria.mascarar_dado_pessoal(texto), "motivo": "aprovacao_nao_entendida",
                                "aprovacao_pendente": self.pendente})
            if self.tentativas_aprovacao < config.TENTATIVAS_RESPOSTA_APROVACAO:
                return {"tipo": "aprovacao", "texto": "Não entendi sua resposta. " + cartao_aprovacao(self.pendente),
                        "payload": self.pendente}
            resposta = {"decisao": "rejeitar", "motivo": "resposta_nao_entendida"}
        resposta["texto_cliente"] = texto[:200]
        return self.decidir(resposta)

    def _estado(self) -> dict:
        return self.grafo.get_state(self.cfg).values

    def _invocar(self, entrada, texto_cliente: str, novo_turno: bool) -> dict:
        self.erro = None
        estado_antes = self._estado() if self.turnos else {}
        tokens_antes = (estado_antes.get("tokens_entrada", 0), estado_antes.get("tokens_saida", 0))
        atributos = {
            "app.contrato": self.contrato,
            "app.identidade.origem": self.identidade["origem"],
            "app.identidade.contrato_digitado_ignorado": self.identidade.get("contrato_digitado_ignorado"),
            "app.turno.tipo": "mensagem" if novo_turno else "retomada_aprovacao",
            # minimização: o trace mascara dado pessoal, mas guarda a tentativa de injeção (auditoria)
            "app.entrada": memoria.mascarar_dado_pessoal(texto_cliente)[:LIMITE_ENTRADA],
            "app.prompt.sistema": config.PROMPT_SISTEMA,
            "app.prompt.sistema.sha256": prompts_em_uso()["sistema"]["sha256"],
            "app.prompt.procedural.sha256": prompts_em_uso()["procedural"]["sha256"],
            "app.commit": _commit(),
            "gen_ai.request.temperature": config.TEMPERATURE,
        }
        with obs.span_turno(self.thread_id, getattr(self.llm, "modelo", config.MODELO), atributos) as raiz:
            try:
                resultado = self.grafo.invoke(entrada, self.cfg)
            except GraphRecursionError:
                self.erro = "recursion_limit"
                resultado = self._estado()
            interrupcao = resultado.get("__interrupt__")
            estado = self._estado()
            if interrupcao:
                self.pendente = interrupcao[0].value
                motivo = "aguardando_humano"
            else:
                motivo = self.erro or estado.get("motivo_parada") or "resposta_final"
            saida = None if interrupcao else (estado.get("saida") or {})
            ent = estado.get("tokens_entrada", 0) - tokens_antes[0]
            sai = estado.get("tokens_saida", 0) - tokens_antes[1]
            raiz.set_attribute("app.motivo_termino", motivo)
            raiz.set_attribute("app.turno", estado.get("turno", 0))
            raiz.set_attribute("app.voltas", estado.get("voltas", 0) or 0)
            raiz.set_attribute("gen_ai.usage.input_tokens", ent)
            raiz.set_attribute("gen_ai.usage.output_tokens", sai)
            raiz.set_attribute("app.custo_usd", obs.custo_usd(ent, sai))
            trechos = sorted({tr for t in estado.get("trajetoria", []) if t.get("nome") == "consultar_base_conhecimento"
                              for tr in [x["id"] for x in t["resultado"].get("trechos", [])]})
            if trechos:
                raiz.set_attribute("app.rag.trechos_recuperados", trechos)
            if saida:
                raiz.set_attribute("app.saida.resultado", obs.texto_curto(saida.get("resultado", "")))
                raiz.set_attribute("app.saida.suficiente", bool(saida.get("suficiente")))
                raiz.set_attribute("app.saida.encaminhar_humano", bool(saida.get("encaminhar_humano")))
                raiz.set_attribute("app.saida.fontes", [f"{f['tipo']}:{f['id']}" for f in saida.get("fontes", [])])
                if saida.get("afirmacoes_bloqueadas"):
                    raiz.set_attribute("app.saida.afirmacoes_bloqueadas", saida["afirmacoes_bloqueadas"])
                if saida.get("motivo_insuficiencia"):
                    raiz.set_attribute("app.saida.motivo_insuficiencia", saida["motivo_insuficiencia"])
            if self.pendente and interrupcao:
                raiz.add_event("aguardando_aprovacao", {"app.aprovacao.payload": obs.texto_curto(self.pendente)})
            trace_id = format(raiz.get_span_context().trace_id, "032x")
        self.encerrada = bool(saida and saida.get("encaminhar_humano"))
        turno = {"cliente": memoria.mascarar_dado_pessoal(texto_cliente), "motivo": motivo, "trace_id": trace_id,
                 "tokens_entrada": ent, "tokens_saida": sai}
        if interrupcao:
            turno["aprovacao_pendente"] = self.pendente
        else:
            turno["saida"] = saida
        self.turnos.append(turno)
        self._gravar_log(estado, motivo)
        if interrupcao:
            return {"tipo": "aprovacao", "texto": cartao_aprovacao(self.pendente), "payload": self.pendente,
                    "trace_id": trace_id}
        return {"tipo": "resposta", "texto": saida.get("resultado", ""), "saida": saida, "motivo": motivo,
                "trace_id": trace_id, "encerrada": self.encerrada}

    def registro(self) -> dict:
        estado = self._estado()
        return {
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
            "versao_sistema": config.VERSAO_SISTEMA,
            "commit": _commit(),
            "modelo": getattr(self.llm, "modelo", config.MODELO),
            "temperature": config.TEMPERATURE,
            "prompts": prompts_em_uso(),
            "thread_id": self.thread_id,
            "contrato": self.contrato,
            "identidade": self.identidade,
            "mensagem_inicial": memoria.mascarar_dado_pessoal(estado.get("mensagem_inicial") or ""),
            "turnos": self.turnos,
            "trajetoria": estado.get("trajetoria", []),
            "pausas_de_aprovacao": self.pausas,
            "voltas": estado.get("voltas"),
            "tokens": estado.get("tokens"),
            "tokens_entrada": estado.get("tokens_entrada"),
            "tokens_saida": estado.get("tokens_saida"),
            "segundos_ativos": round(estado.get("segundos_ativos", 0.0) or 0.0, 2),
            "motivo_parada": self.turnos[-1]["motivo"] if self.turnos else None,
            "saida": estado.get("saida"),
        }

    def _gravar_log(self, estado, motivo):
        os.makedirs(self.pasta_logs, exist_ok=True)
        caminho = os.path.join(self.pasta_logs, f"{self.rotulo}.json")
        with open(caminho, "w", encoding="utf-8") as arquivo:
            json.dump(self.registro(), arquivo, ensure_ascii=False, indent=2)
        self.arquivo_log = caminho


# ----------------------------------------------------------------- terminal

def _ler_com_prazo(prompt: str, segundos: Optional[int]) -> Optional[str]:
    if not segundos:
        return input(prompt)
    caixa = {}

    def ler():
        try:
            caixa["texto"] = input(prompt)
        except EOFError:
            caixa["texto"] = "/sair"

    t = threading.Thread(target=ler, daemon=True)
    t.start()
    t.join(segundos)
    return caixa.get("texto")


def _criar_llm(nome: str):
    if nome == "regras":
        from .modelo_regras import ModeloRegras
        return ModeloRegras()
    return ClienteLLM()


def main():
    p = argparse.ArgumentParser(description="Chat do agente de suporte técnico doméstico")
    p.add_argument("--telefone", help="telefone do cliente (simula o número autenticado do WhatsApp)")
    p.add_argument("--modelo", choices=["real", "regras"], default="real",
                   help="real = o modelo do .env; regras = substituto determinístico, sem chave de API")
    p.add_argument("--debug", action="store_true", help="mostra o objeto de saída completo a cada resposta")
    a = p.parse_args()
    db.inicializar()
    telefone = a.telefone or input("Telefone do cliente (ex.: +5511900000004): ").strip()
    llm = _criar_llm(a.modelo)

    def nova():
        conversa = Conversa(telefone=telefone, llm=llm)
        print(f"\n[conversa {conversa.thread_id} · contrato {conversa.contrato} (pelo telefone) · "
              f"modelo {getattr(llm, 'modelo', '?')} · versão {config.VERSAO_SISTEMA}]")
        print("Agente: Olá! Sou o assistente de suporte técnico. Me conte o que está acontecendo com a sua internet.")
        print("        (comandos: /nova começa outra conversa, /sair encerra)")
        return conversa

    try:
        conversa = nova()
    except SessaoRecusada:
        print("Telefone sem cadastro: este canal só atende clientes com telefone vinculado a um contrato.")
        return
    while True:
        prazo = conversa.pendente["prazo_segundos"] if conversa.pendente else None
        texto = _ler_com_prazo("\nVocê: ", prazo)
        if texto is None:
            print("\n(prazo da aprovação esgotado)")
            r = conversa.expirar()
        else:
            texto = texto.strip()
            if texto in ("/sair", "sair"):
                break
            if texto == "/nova":
                conversa.fechar()
                conversa = nova()
                continue
            if not texto:
                continue
            r = conversa.enviar(texto)
        print(f"\nAgente: {r['texto']}")
        if a.debug and r.get("saida"):
            print(json.dumps(r["saida"], ensure_ascii=False, indent=2))
        if r.get("tipo") == "resposta":
            s = r["saida"]
            print(f"        [motivo: {r['motivo']} · suficiente: {s.get('suficiente')} · "
                  f"fontes: {[f['id'] for f in s.get('fontes', [])]} · trace {r['trace_id'][:8]}]")
        if r.get("encerrada") or r.get("tipo") == "encerrada":
            print("        [conversa transferida para um atendente humano — /nova para começar outra, /sair para sair]")
    conversa.fechar()
    print(f"Log da conversa: {getattr(conversa, 'arquivo_log', '-')}")


if __name__ == "__main__":
    main()
