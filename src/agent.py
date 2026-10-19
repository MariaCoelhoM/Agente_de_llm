import argparse
import datetime
import hashlib
import json
import os
import sqlite3
import subprocess
import threading
import uuid
from typing import Callable, Optional

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.errors import GraphRecursionError
from langgraph.types import Command

from . import config, db
from .grafo import obter_grafo
from .llm import ClienteLLM


def _commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, cwd=config.RAIZ, timeout=5).stdout.strip() or "sem-git"
    except Exception:
        return "sem-git"


def prompts_em_uso() -> dict:
    usados = {}
    for papel, nome in (("sistema", config.PROMPT_SISTEMA), ("procedural", config.PROMPT_PROCEDURAL)):
        caminho = os.path.join(config.PASTA_PROMPTS, nome)
        with open(caminho, "rb") as arquivo:
            usados[papel] = {"arquivo": nome, "sha256": hashlib.sha256(arquivo.read()).hexdigest()[:12]}
    return usados


def decisor_terminal(payload: dict) -> dict:
    print("\n=== APROVAÇÃO NECESSÁRIA ===")
    print(f"Ação: {payload['acao']}  contrato={payload['contrato']}  data={payload['data_proposta']}")
    print(f"Consequência: {payload['consequencia']}")
    print(f"Prazo: {payload['prazo_segundos']}s. Opções: aprovar | rejeitar | editar AAAA-MM-DD")
    caixa = {}

    def ler():
        caixa["texto"] = input("> ").strip()

    t = threading.Thread(target=ler, daemon=True)
    t.start()
    t.join(payload["prazo_segundos"])
    if "texto" not in caixa:
        print("\n(prazo esgotado)")
        return {"decisao": "expirou"}
    partes = caixa["texto"].split()
    if partes and partes[0] == "editar" and len(partes) > 1:
        return {"decisao": "editar", "data": partes[1]}
    return {"decisao": partes[0] if partes else "rejeitar"}


def decisor_fixo(decisao: str, data: Optional[str] = None) -> Callable[[dict], dict]:
    def decidir(payload):
        return {"decisao": decisao, **({"data": data} if data else {})}
    return decidir


def executar_atendimento(
    contrato: str,
    mensagem: str,
    llm=None,
    decisor: Callable[[dict], dict] = decisor_terminal,
    checkpointer=None,
    pasta_logs: Optional[str] = None,
    rotulo: Optional[str] = None,
) -> dict:
    llm = llm or ClienteLLM()
    proprio = checkpointer is None
    conexao = None
    if proprio:
        os.makedirs(os.path.dirname(config.CAMINHO_CHECKPOINTS), exist_ok=True)
        conexao = sqlite3.connect(config.CAMINHO_CHECKPOINTS, check_same_thread=False)
        checkpointer = SqliteSaver(conexao)
    try:
        grafo = obter_grafo(llm, checkpointer)
        thread_id = f"{contrato}:{uuid.uuid4().hex[:8]}"
        cfg = {"configurable": {"thread_id": thread_id}, "recursion_limit": config.RECURSION_LIMIT}
        entrada = {"thread_id": thread_id, "contrato": contrato, "mensagem": mensagem}
        pausas, erro = [], None
        try:
            resultado = grafo.invoke(entrada, cfg)
            while resultado.get("__interrupt__"):
                payload = resultado["__interrupt__"][0].value
                resposta = decisor(payload)
                pausas.append({"payload": payload, "resposta": resposta})
                resultado = grafo.invoke(Command(resume=resposta), cfg)
        except GraphRecursionError:
            erro = "recursion_limit"
            resultado = grafo.get_state(cfg).values
        registro = {
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
            "commit": _commit(),
            "modelo": getattr(llm, "modelo", config.MODELO),
            "temperature": config.TEMPERATURE,
            "prompts": prompts_em_uso(),
            "thread_id": thread_id,
            "contrato": contrato,
            "mensagem_inicial": mensagem,
            "trajetoria": resultado.get("trajetoria", []),
            "pausas_de_aprovacao": pausas,
            "voltas": resultado.get("voltas"),
            "tokens": resultado.get("tokens"),
            "segundos_ativos": round(resultado.get("segundos_ativos", 0.0), 2),
            "motivo_parada": erro or resultado.get("motivo_parada"),
            "saida": resultado.get("saida"),
        }
    finally:
        if conexao:
            conexao.close()
    pasta = pasta_logs or config.PASTA_LOGS
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, f"{rotulo or 'caso_' + contrato}.json")
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump(registro, arquivo, ensure_ascii=False, indent=2)
    registro["arquivo_log"] = caminho
    return registro


def main():
    p = argparse.ArgumentParser()
    p.add_argument("contrato")
    p.add_argument("mensagem", nargs="?", default="Minha internet caiu.")
    p.add_argument("--decisao", choices=["aprovar", "rejeitar", "editar", "expirou"])
    p.add_argument("--data")
    p.add_argument("--rotulo")
    a = p.parse_args()
    db.inicializar()
    decisor = decisor_fixo(a.decisao, a.data) if a.decisao else decisor_terminal
    r = executar_atendimento(a.contrato, a.mensagem, decisor=decisor, rotulo=a.rotulo)
    print(f"\nResposta: {r['saida']['resultado']}")
    print(f"Fontes: {[f['id'] for f in r['saida']['fontes']]}  suficiente={r['saida']['suficiente']}")
    print(f"Parou por: {r['motivo_parada']}   Log: {r['arquivo_log']}")


if __name__ == "__main__":
    main()