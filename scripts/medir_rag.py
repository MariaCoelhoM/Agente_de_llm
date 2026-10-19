import argparse
import json
import os

from src import config, rag


def carregar_perguntas():
    caminho = os.path.join(config.PASTA_DADOS, "perguntas_rag.json")
    with open(caminho, encoding="utf-8") as arquivo:
        return json.load(arquivo)


def medir(incluir_revogados: bool, ks):
    indice = rag.construir_indice(incluir_revogados=incluir_revogados)
    perguntas = carregar_perguntas()
    linhas = []
    acertos = {k: 0 for k in ks}
    total_com_resposta = 0
    portao_certo = 0
    for q in perguntas:
        achados = indice.buscar(q["pergunta"], k=max(ks))
        ids = [a["trecho"].id for a in achados]
        docs = [a["trecho"].doc for a in achados]
        cobertura = achados[0]["cobertura"] if achados else 0.0
        passa_portao = bool(achados) and cobertura >= config.RAG_COBERTURA_MINIMA
        esperado = set(q["esperado_corpus"])
        if esperado:
            total_com_resposta += 1
            for k in ks:
                if esperado & set(ids[:k]):
                    acertos[k] += 1
        deveria_passar = bool(esperado)
        if q["fonte_esperada"] == "corpus":
            portao_certo += int(passa_portao)
        elif q["fonte_esperada"] == "nenhuma":
            portao_certo += int(not passa_portao)
        linhas.append(
            {
                "id": q["id"],
                "forma": q["forma"],
                "top": list(zip(ids, docs))[:3],
                "cobertura_top1": cobertura,
                "passa_portao": passa_portao,
                "esperado": sorted(esperado),
                "deveria_passar": deveria_passar,
            }
        )
    return linhas, acertos, total_com_resposta, portao_certo


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--revogados", action="store_true")
    parser.add_argument("--k", type=int, action="append")
    args = parser.parse_args()
    ks = sorted(args.k or [1, 3])

    linhas, acertos, total, portao = medir(args.revogados, ks)
    print(f"revogados incluídos: {args.revogados}")
    for linha in linhas:
        topo = ", ".join(f"{i}({d[:2]})" for i, d in linha["top"]) or "-"
        print(
            f"{linha['id']} {linha['forma']:9} cob={linha['cobertura_top1']:.2f} "
            f"portão={'passa' if linha['passa_portao'] else 'barra '} "
            f"esperado={linha['esperado']} top={topo}"
        )
    for k in ks:
        print(f"acerto@{k}: {acertos[k]}/{total}")
    print(f"portão correto (corpus/nenhuma): {portao}/{sum(1 for l in linhas if l['esperado'] or l['forma'] != 'registro')}")


if __name__ == "__main__":
    main()
