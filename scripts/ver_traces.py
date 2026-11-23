"""Mostra os traces gravados em arquivo como árvore de spans.

  python -m scripts.ver_traces                         # últimos 5 traces de logs/traces/
  python -m scripts.ver_traces --n 20
  python -m scripts.ver_traces --trace 3f2a            # um trace (prefixo do trace_id)
  python -m scripts.ver_traces --arquivo evals/resultados/3.0.0_regras/traces.jsonl --conversa C004
  python -m scripts.ver_traces --atributos             # mostra todos os atributos de cada span
"""
import argparse
import glob
import json
import os
from collections import defaultdict

from src import config

DESTAQUE = ("app.motivo_termino", "app.versao_sistema", "app.entrada", "app.saida.resultado",
            "app.saida.suficiente", "app.saida.afirmacoes_bloqueadas", "app.custo_usd",
            "gen_ai.usage.input_tokens", "gen_ai.usage.output_tokens", "gen_ai.tool.call.arguments",
            "gen_ai.tool.call.result", "app.rag.trechos", "app.contrato_sobrescrito", "error.type")


def carregar(arquivos):
    spans = []
    for a in arquivos:
        with open(a, encoding="utf-8") as f:
            spans += [json.loads(l) for l in f if l.strip()]
    return spans


def imprimir(spans, todos):
    filhos = defaultdict(list)
    for s in spans:
        filhos[s["parent_id"]].append(s)

    def rec(s, nivel):
        marca = " [ERRO]" if s["status"] == "ERROR" else ""
        print(f"{'  ' * nivel}{s['nome']}  {s['duracao_ms']} ms{marca}")
        for k, v in s["atributos"].items():
            if todos or k in DESTAQUE:
                print(f"{'  ' * nivel}    {k} = {str(v)[:160]}")
        for e in s["eventos"]:
            print(f"{'  ' * nivel}    evento {e['nome']}: " + ", ".join(f"{k}={str(v)[:60]}" for k, v in e["atributos"].items()))
        for f in sorted(filhos[s["span_id"]], key=lambda x: x["inicio"]):
            rec(f, nivel + 1)

    for raiz in filhos[None]:
        a = raiz["atributos"]
        print(f"\ntrace {raiz['trace_id']}  conversa {a.get('gen_ai.conversation.id')}  {raiz['inicio']}")
        rec(raiz, 1)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--arquivo", nargs="*")
    p.add_argument("--trace")
    p.add_argument("--conversa", help="prefixo do gen_ai.conversation.id (ex.: C004)")
    p.add_argument("--n", type=int, default=5)
    p.add_argument("--atributos", action="store_true")
    a = p.parse_args()
    arquivos = a.arquivo or sorted(glob.glob(os.path.join(config.PASTA_TRACES, "*.jsonl")))
    if not arquivos:
        print(f"nenhum trace em {config.PASTA_TRACES}: converse com o agente (python -m src.chat) primeiro")
        return
    spans = carregar(arquivos)
    raizes = [s for s in spans if s["parent_id"] is None]
    if a.trace:
        raizes = [r for r in raizes if r["trace_id"].startswith(a.trace)]
    if a.conversa:
        raizes = [r for r in raizes if str(r["atributos"].get("gen_ai.conversation.id", "")).startswith(a.conversa)]
    escolhidos = {r["trace_id"] for r in raizes[-a.n:]} if not a.trace else {r["trace_id"] for r in raizes}
    imprimir([s for s in spans if s["trace_id"] in escolhidos], a.atributos)


if __name__ == "__main__":
    main()
