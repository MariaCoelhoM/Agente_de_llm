"""
Métricas e SLO a partir dos traces (docs/observabilidade.md §3 e §4).

  python -m evals.metricas evals/resultados/2.1.0_regras evals/resultados/3.0.0_regras
  python -m evals.metricas logs/traces            # traces do uso do chat

Uma EXECUÇÃO é uma raiz `invoke_agent` (um turno da conversa). Tudo é cortado
por `app.versao_sistema`: um número que mistura versões soma sistemas diferentes.

Reporta, por versão: latência p50 e p95 (duração da raiz), custo por execução
(tokens x preço do modelo, atributo app.custo_usd), distribuição dos motivos
de término, taxa de erro por ferramenta (spans execute_tool com status ERROR)
e o SLI/SLO de qualidade.
"""
import glob
import json
import os
import sys
from collections import Counter, defaultdict

# SLI de qualidade (docs/observabilidade.md §4): fração das execuções válidas
# que terminam BEM. "Bem" = o sistema decidiu terminar, sem esgotar orçamento,
# sem erro, e sem que o verificador tenha precisado corrigir a resposta.
MOTIVOS_BONS = {"resposta_final", "aguardando_humano", "entrada_incompleta", "encaminhado_humano"}
MOTIVOS_FORA_DO_SLI = {"agente_suspenso"}  # decisão da operação, não falha do agente
OBJETIVO_SLO = 95.0
JANELA = "7 dias"


def _spans(caminhos):
    arquivos = []
    for c in caminhos:
        arquivos += sorted(glob.glob(os.path.join(c, "*.jsonl"))) if os.path.isdir(c) else [c]
    for arq in arquivos:
        if os.path.basename(arq) in ("casos.jsonl", "juiz.jsonl"):
            continue
        with open(arq, encoding="utf-8") as f:
            for linha in f:
                if linha.strip():
                    yield json.loads(linha)


def percentil(valores, p):
    if not valores:
        return 0.0
    v = sorted(valores)
    k = (len(v) - 1) * p / 100
    i, frac = int(k), k - int(k)
    return round(v[i] + (v[min(i + 1, len(v) - 1)] - v[i]) * frac, 1)


def calcular(caminhos):
    spans = list(_spans(caminhos))
    raizes = [s for s in spans if s["parent_id"] is None and s["nome"].startswith("invoke_agent")]
    versao_do_trace = {s["trace_id"]: s["atributos"].get("app.versao_sistema", "?") for s in raizes}
    por_versao = defaultdict(lambda: {"raizes": [], "ferramentas": []})
    for s in raizes:
        por_versao[versao_do_trace[s["trace_id"]]]["raizes"].append(s)
    for s in spans:
        if s["nome"].startswith("execute_tool"):
            por_versao[versao_do_trace.get(s["trace_id"], "?")]["ferramentas"].append(s)

    saida = {}
    for versao, d in sorted(por_versao.items()):
        r = d["raizes"]
        motivos = Counter(x["atributos"].get("app.motivo_termino", "?") for x in r)
        custos = [x["atributos"].get("app.custo_usd", 0.0) for x in r]
        validas = [x for x in r if x["atributos"].get("app.motivo_termino") not in MOTIVOS_FORA_DO_SLI]
        boas = [x for x in validas if x["atributos"].get("app.motivo_termino") in MOTIVOS_BONS
                and not x["atributos"].get("app.saida.afirmacoes_bloqueadas")]
        sli = round(100 * len(boas) / len(validas), 1) if validas else 0.0
        orcamento = 100 - OBJETIVO_SLO
        consumido = round(100 * (100 - sli) / orcamento, 1) if orcamento else 0.0
        erros = defaultdict(lambda: [0, 0])
        for f in d["ferramentas"]:
            nome = f["atributos"].get("gen_ai.tool.name", "?")
            erros[nome][1] += 1
            if f["status"] == "ERROR":
                erros[nome][0] += 1
        saida[versao] = {
            "execucoes": len(r),
            "conversas": len({x["atributos"].get("gen_ai.conversation.id") for x in r}),
            "latencia_ms_p50": percentil([x["duracao_ms"] for x in r], 50),
            "latencia_ms_p95": percentil([x["duracao_ms"] for x in r], 95),
            "custo_usd_por_execucao": round(sum(custos) / len(r), 6) if r else 0.0,
            "custo_usd_total": round(sum(custos), 6),
            "tokens_entrada_media": round(sum(x["atributos"].get("gen_ai.usage.input_tokens", 0) for x in r) / len(r), 1) if r else 0,
            "tokens_saida_media": round(sum(x["atributos"].get("gen_ai.usage.output_tokens", 0) for x in r) / len(r), 1) if r else 0,
            "motivos_de_termino": dict(motivos.most_common()),
            "erro_por_ferramenta": {n: {"erros": e, "chamadas": t, "taxa_%": round(100 * e / t, 1)}
                                    for n, (e, t) in sorted(erros.items())},
            "respostas_corrigidas_pelo_verificador": sum(1 for x in r if x["atributos"].get("app.saida.afirmacoes_bloqueadas")),
            "slo": {"sli": "execuções que terminam bem / execuções válidas", "boas": len(boas),
                    "validas": len(validas), "valor_%": sli, "objetivo_%": OBJETIVO_SLO, "janela": JANELA,
                    "cumprido": sli >= OBJETIVO_SLO, "orcamento_de_erro_consumido_%": consumido},
        }
    return saida


def main(caminhos):
    resultado = calcular(caminhos)
    for versao, m in resultado.items():
        print(f"\n=== versão {versao}: {m['execucoes']} execuções em {m['conversas']} conversas")
        print(f"latência p50 {m['latencia_ms_p50']} ms · p95 {m['latencia_ms_p95']} ms")
        print(f"custo por execução US$ {m['custo_usd_por_execucao']:.6f} (total US$ {m['custo_usd_total']:.6f}) · "
              f"tokens médios entrada {m['tokens_entrada_media']} / saída {m['tokens_saida_media']}")
        print("motivos de término:", ", ".join(f"{k} {v}" for k, v in m["motivos_de_termino"].items()))
        print("erro por ferramenta:", ", ".join(f"{k} {v['erros']}/{v['chamadas']} ({v['taxa_%']}%)"
                                                for k, v in m["erro_por_ferramenta"].items()))
        print(f"respostas corrigidas pelo verificador (C4): {m['respostas_corrigidas_pelo_verificador']}")
        s = m["slo"]
        print(f"SLO qualidade: {s['boas']}/{s['validas']} = {s['valor_%']}% (objetivo {s['objetivo_%']}% em {s['janela']}) "
              f"-> {'CUMPRIDO' if s['cumprido'] else 'VIOLADO'}; orçamento de erro consumido {s['orcamento_de_erro_consumido_%']}%")
    return resultado


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("uso: python -m evals.metricas <pasta-ou-arquivo> [...]")
    r = main([a for a in sys.argv[1:] if not a.startswith("--")])
    if "--json" in sys.argv:
        print(json.dumps(r, ensure_ascii=False, indent=2))
