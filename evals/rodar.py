"""
Roda o golden dataset contra o sistema entregue e grava a rodada.

  python -m evals.rodar --versao 3.0.0                          # modelo do .env
  python -m evals.rodar --versao 3.0.0 --modelo regras          # sem chave de API
  python -m evals.rodar --versao 2.1.0 --versao-anterior        # controles da Parte 3 desligados
  python -m evals.rodar --versao 3.0.0 --casos G07 G24          # só alguns casos

Cada caso roda em bancos próprios (provedor, memória, checkpoints), pelo mesmo
caminho que o chat usa: `src.chat.Conversa` (telefone -> contrato -> grafo).
As respostas à pausa de aprovação são TEXTO, lido pelo código do chat, como
um cliente digitaria. Nada é chamado por fora do sistema.

Saída: evals/resultados/<rodada>/
  meta.json      versão, modelo, controles, dataset, commit, data
  casos.jsonl    um registro por caso: verificações, respostas, trace_ids
  resumo.json    acerto por classe e média (o que evals.comparar lê)
  traces.jsonl   os traces OpenTelemetry de todas as execuções da rodada
"""
import argparse
import datetime
import json
import os
import re
import shutil
import sqlite3
import tempfile
import time

from src import config, db, memoria, tools
from src import observabilidade as obs
from src.chat import Conversa, _commit
from src.grafo import verificar_afirmacoes
from src.schemas import RespostaAtendimento

from .verificacoes import NIVEIS, verificar

PASTA = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(PASTA, "dataset.jsonl")


def carregar_dataset(caminho=DATASET):
    with open(caminho, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def _data(rel: str) -> str:
    return (tools._hoje() + datetime.timedelta(days=int(rel))).isoformat()


def _texto_aprovacao(modelo: str) -> str:
    return re.sub(r"\{([+-]\d+)\}",
                  lambda m: datetime.date.fromisoformat(_data(m.group(1))).strftime("%d/%m"), modelo)


def criar_llm(nome: str):
    if nome == "regras":
        from src.modelo_regras import ModeloRegras
        return ModeloRegras()
    from src.llm import ClienteLLM
    return ClienteLLM()


def rodar_caso(caso: dict, nome_llm: str, pasta_tmp: str) -> dict:
    # bancos isolados por caso
    db.DB_PATH = os.path.join(pasta_tmp, "provedor.db")
    config.CAMINHO_MEMORIA = os.path.join(pasta_tmp, "memoria.db")
    config.CAMINHO_CHECKPOINTS = os.path.join(pasta_tmp, "checkpoints.db")
    config.PASTA_LOGS = os.path.join(pasta_tmp, "logs")
    db.inicializar()

    llm = criar_llm(nome_llm)
    execucoes, conversas = [], []
    inicio = time.monotonic()
    for c in caso["entrada"]["conversas"]:
        conversa = Conversa(telefone=c.get("telefone"), contrato=c.get("contrato"),
                            contrato_digitado=c.get("contrato_digitado"), llm=llm,
                            rotulo=f"{caso['id']}_{len(conversas)}")
        aprovacoes = list(c.get("aprovacoes", []))
        respostas = []
        try:
            for texto in c["turnos"]:
                t0 = time.monotonic()
                r = conversa.enviar(texto)
                respostas.append({"cliente": texto, "tipo": r["tipo"], "texto": r.get("texto"),
                                  "segundos": round(time.monotonic() - t0, 3)})
                while r["tipo"] == "aprovacao":
                    resposta = aprovacoes.pop(0) if aprovacoes else None
                    t0 = time.monotonic()
                    r = conversa.expirar() if resposta is None else conversa.enviar(_texto_aprovacao(resposta))
                    respostas.append({"cliente": resposta if resposta is None else _texto_aprovacao(resposta),
                                      "tipo": r["tipo"], "texto": r.get("texto"),
                                      "segundos": round(time.monotonic() - t0, 3)})
                if r["tipo"] == "encerrada":
                    break
            reg = conversa.registro()
        finally:
            conversa.fechar()
        conversas.append({"registro": reg, "respostas": respostas})
    segundos = round(time.monotonic() - inicio, 3)

    # estado do mundo depois da execução (avaliação de resultado)
    conn = db.conectar()
    visitas = [tuple(l) for l in conn.execute("SELECT contrato, data FROM visitas ORDER BY id")]
    conn.close()
    mem = sqlite3.connect(config.CAMINHO_MEMORIA)
    memoria_texto = " ".join(str(v) for linha in mem.execute("SELECT * FROM episodica").fetchall() for v in linha)
    memoria_texto += " ".join(str(v) for linha in mem.execute("SELECT * FROM semantica").fetchall() for v in linha)
    mem.close()

    ultima = conversas[-1]
    reg = ultima["registro"]
    saida = reg.get("saida") or {}
    contexto = {
        "conversas": conversas,
        "trajetoria": [t for cv in conversas for t in cv["registro"]["trajetoria"]],
        "trajetoria_final": reg["trajetoria"],
        "saida": saida,
        "motivo_final": reg["motivo_parada"],
        "pausas": sum(len(cv["registro"]["pausas_de_aprovacao"]) for cv in conversas),
        "visitas": visitas,
        "memoria_texto": memoria_texto,
        "chamadas_ao_modelo": getattr(llm, "chamadas", None),
        "turnos_respondidos": sum(1 for r in ultima["respostas"] if r["tipo"] == "resposta"),
        "data": _data,
        "verificar_afirmacoes": verificar_afirmacoes,
        "schema": RespostaAtendimento,
    }
    checagens = verificar(caso["esperado"], contexto)
    return {
        "id": caso["id"], "classe": caso["classe"], "origem": caso["origem"],
        "passou": all(c["ok"] for c in checagens),
        "checagens": checagens,
        "motivo_final": reg["motivo_parada"],
        "resposta_final": saida.get("resultado"),
        "saida": saida,
        "respostas": [r for cv in conversas for r in cv["respostas"]],
        "trace_ids": [t["trace_id"] for cv in conversas for t in cv["registro"]["turnos"]],
        "visitas": visitas,
        "tokens_entrada": sum(cv["registro"].get("tokens_entrada") or 0 for cv in conversas),
        "tokens_saida": sum(cv["registro"].get("tokens_saida") or 0 for cv in conversas),
        "segundos": segundos,
        "trajetoria": [{k: v for k, v in t.items() if k in ("tipo", "nome", "args", "resultado", "decisao", "n")}
                       for t in contexto["trajetoria"]],
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--versao", required=True, help="rótulo da versão do sistema nesta rodada")
    p.add_argument("--modelo", choices=["real", "regras"], default="real")
    p.add_argument("--versao-anterior", action="store_true",
                   help="desliga os controles C1, C3 e C4 da Parte 3 (reproduz a versão 2.x nesses caminhos)")
    p.add_argument("--casos", nargs="*")
    p.add_argument("--nome", help="nome da pasta da rodada (padrão: versão_modelo_data)")
    a = p.parse_args()

    if a.versao_anterior:
        for chave in config.CONTROLES:
            config.CONTROLES[chave] = False
    config.VERSAO_SISTEMA = a.versao
    dataset = carregar_dataset()
    if a.casos:
        dataset = [c for c in dataset if c["id"] in a.casos]
    with open(os.path.join(PASTA, "dataset_versao.json"), encoding="utf-8") as f:
        versao_dataset = json.load(f)["versao"]

    agora = datetime.datetime.now()
    nome = a.nome or f"{a.versao}_{a.modelo}_{agora:%Y%m%d-%H%M%S}"
    destino = os.path.join(PASTA, "resultados", nome)
    os.makedirs(destino, exist_ok=True)
    caminho_traces = os.path.join(destino, "traces.jsonl")
    if os.path.exists(caminho_traces):
        os.remove(caminho_traces)
    obs.redirecionar(caminho_traces)

    originais = (db.DB_PATH, config.CAMINHO_MEMORIA, config.CAMINHO_CHECKPOINTS, config.PASTA_LOGS)
    resultados = []
    try:
        for caso in dataset:
            pasta_tmp = tempfile.mkdtemp(prefix=f"eval_{caso['id']}_")
            try:
                r = rodar_caso(caso, a.modelo, pasta_tmp)
            except Exception as erro:  # um caso que quebra é resultado, não aborta a rodada
                r = {"id": caso["id"], "classe": caso["classe"], "origem": caso["origem"], "passou": False,
                     "checagens": [{"nome": "execucao", "nivel": "deterministico", "ok": False,
                                    "detalhe": f"{type(erro).__name__}: {erro}"}]}
            finally:
                shutil.rmtree(pasta_tmp, ignore_errors=True)
            resultados.append(r)
            print(f"{r['id']:4} {r['classe']:17} {'ok ' if r['passou'] else 'FALHOU'}  "
                  + "; ".join(c["nome"] + ": " + c["detalhe"] for c in r["checagens"] if not c["ok"]))
    finally:
        db.DB_PATH, config.CAMINHO_MEMORIA, config.CAMINHO_CHECKPOINTS, config.PASTA_LOGS = originais
        obs.descarregar()
        obs.redirecionar(None)

    classes = sorted({r["classe"] for r in resultados})
    por_classe = {c: round(100 * sum(r["passou"] for r in resultados if r["classe"] == c)
                           / sum(1 for r in resultados if r["classe"] == c), 1) for c in classes}
    por_nivel = {}
    for nivel in NIVEIS:
        chk = [c for r in resultados for c in r["checagens"] if c["nivel"] == nivel]
        if chk:
            por_nivel[nivel] = {"checagens": len(chk), "ok": sum(c["ok"] for c in chk)}
    origens = {o: sum(1 for c in dataset if c["origem"] == o) for o in ("producao", "desenvolvimento", "sintetico")}
    resumo = {
        "rodada": nome, "versao": a.versao, "modelo": a.modelo, "versao_dataset": versao_dataset,
        "casos": len(resultados), "origens": origens,
        "por_classe": por_classe,
        "media": round(sum(por_classe.values()) / len(por_classe), 1) if por_classe else 0.0,
        "acerto_geral": round(100 * sum(r["passou"] for r in resultados) / len(resultados), 1) if resultados else 0.0,
        "por_nivel": por_nivel,
        "falhas": [r["id"] for r in resultados if not r["passou"]],
        "sinteticos_sem_revisao": [c["id"] for c in dataset if c["origem"] == "sintetico"
                                   and not (c.get("revisao") or {}).get("por")],
    }
    meta = {
        "rodada": nome, "versao": a.versao, "modelo": a.modelo,
        "modelo_id": os.environ.get("LLM_MODEL", config.MODELO) if a.modelo == "real" else "regras-v1",
        "controles": dict(config.CONTROLES), "commit": _commit(), "data": agora.isoformat(timespec="seconds"),
        "hoje_do_sistema": tools._hoje().isoformat(), "versao_dataset": versao_dataset,
        "comando": "python -m evals.rodar " + " ".join(os.sys.argv[1:]),
    }
    with open(os.path.join(destino, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    with open(os.path.join(destino, "resumo.json"), "w", encoding="utf-8") as f:
        json.dump(resumo, f, ensure_ascii=False, indent=2)
    with open(os.path.join(destino, "casos.jsonl"), "w", encoding="utf-8") as f:
        for r in resultados:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
    print(f"\nrodada {nome}: {resumo['acerto_geral']}% dos casos ({len(resultados)}), média por classe {resumo['media']}%")
    if resumo["sinteticos_sem_revisao"]:
        print(f"AVISO: {len(resumo['sinteticos_sem_revisao'])} casos sintéticos sem revisor declarado "
              f"(campo revisao.por em evals/dataset.jsonl)")
    print(f"gravado em {os.path.relpath(destino, config.RAIZ)}")


if __name__ == "__main__":
    main()
