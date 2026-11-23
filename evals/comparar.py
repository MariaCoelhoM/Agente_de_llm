"""
Compara duas rodadas da suíte.

  python -m evals.comparar evals/resultados/2.1.0_regras evals/resultados/3.0.0_regras
"""
import json
import os
import sys

PASTA = os.path.dirname(os.path.abspath(__file__))


def _ler(pasta):
    with open(os.path.join(pasta, "resumo.json"), encoding="utf-8") as f:
        resumo = json.load(f)
    with open(os.path.join(pasta, "casos.jsonl"), encoding="utf-8") as f:
        casos = {c["id"]: c for c in map(json.loads, f)}
    return resumo, casos


def _juiz():
    caminho = os.path.join(PASTA, "juiz", "validacao.json")
    if not os.path.exists(caminho):
        rubrica = os.path.join(PASTA, "juiz", "rubrica_coerencia.md")
        versao = "?"
        if os.path.exists(rubrica):
            for linha in open(rubrica, encoding="utf-8"):
                if linha.lower().startswith("versão:"):
                    versao = linha.split(":", 1)[1].strip()
        return f"JUIZ rubrica v{versao}   concordância n/d   limiar 85%   (não validado: ver docs/evals.md §3)"
    v = json.load(open(caminho, encoding="utf-8"))
    estado = "adotado" if v["adotado"] else "NÃO adotado"
    return (f"JUIZ rubrica v{v['versao_rubrica']}   concordância {v['concordancia']}%   "
            f"limiar {v['limiar']}%   ({estado})")


def main(a, b):
    ra, ca = _ler(a)
    rb, cb = _ler(b)
    o = rb["origens"]
    if ra["versao_dataset"] != rb["versao_dataset"]:
        print(f"ATENÇÃO: datasets diferentes ({ra['versao_dataset']} x {rb['versao_dataset']})")
    print(f"DATASET v{rb['versao_dataset']}   {rb['casos']} casos   "
          f"(producao {o['producao']} · desenvolvimento {o['desenvolvimento']} · sintetico {o['sintetico']})")
    print(_juiz())
    print(f"A = {ra['rodada']} (modelo {ra['modelo']})   B = {rb['rodada']} (modelo {rb['modelo']})")
    print()
    print(f"{'classe':18}{'versão A':>10}{'versão B':>11}{'delta':>8}")
    for classe in sorted(set(ra["por_classe"]) | set(rb["por_classe"])):
        va, vb = ra["por_classe"].get(classe), rb["por_classe"].get(classe)
        delta = f"{vb - va:+.1f}" if va is not None and vb is not None else "n/d"
        print(f"{classe:18}{va:>9}%{vb:>10}%{delta:>8}")
    print(f"{'MÉDIA':18}{ra['media']:>9}%{rb['media']:>10}%{rb['media'] - ra['media']:>+8.1f}")
    print()
    mudaram = [(i, ca[i]["passou"], cb[i]["passou"]) for i in sorted(set(ca) & set(cb))
               if ca[i]["passou"] != cb[i]["passou"]]
    if mudaram:
        print("casos que mudaram:")
        for i, pa, pb in mudaram:
            motivo = "; ".join(c["nome"] for c in (ca[i] if not pa else cb[i])["checagens"] if not c["ok"])
            print(f"  {i}  {'falhava' if not pa else 'passava'} -> {'passa' if pb else 'FALHA'}   ({motivo})")
    else:
        print("nenhum caso mudou de resultado")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("uso: python -m evals.comparar <rodada-A> <rodada-B>")
    main(sys.argv[1], sys.argv[2])
