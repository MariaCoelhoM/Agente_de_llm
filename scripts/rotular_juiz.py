"""Rotulagem manual dos 20 itens do juiz (evals/juiz/rotulos.jsonl).

Uso (da raiz do repositório):
  python -m scripts.rotular_juiz --por "Seu Nome" --itens 1-5

Mostra, um por vez, o que o cliente escreveu, a trajetória e a resposta, e
pergunta se a resposta é coerente com a trajetória (rubrica em
evals/juiz/rubrica_coerencia.md). Grava no arquivo a cada item, então dá para
interromper com Ctrl+C e continuar depois. Itens já rotulados são pulados.
"""
import argparse
import json
import os

ARQ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "evals", "juiz", "rotulos.jsonl")


def _faixa(texto, n):
    if not texto:
        return list(range(1, n + 1))
    ini, _, fim = texto.partition("-")
    return list(range(int(ini), int(fim or ini) + 1))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--por", required=True, help="nome de quem rotula")
    p.add_argument("--itens", help="faixa de itens, ex.: 1-5 (padrão: todos)")
    a = p.parse_args()

    itens = [json.loads(l) for l in open(ARQ, encoding="utf-8") if l.strip()]
    for n in _faixa(a.itens, len(itens)):
        i = itens[n - 1]
        if i.get("rotulo_humano") in ("coerente", "incoerente"):
            continue
        print(f"\n===== item {n}/{len(itens)}  ({i['id']}) =====")
        print(f"CLIENTE:\n{i['cliente']}\n")
        print(f"TRAJETÓRIA:\n{i['trajetoria']}\n")
        print(f"RESPOSTA:\n{i['resposta']}\n")
        while True:
            r = input("coerente (c) ou incoerente (i)? ").strip().lower()
            if r in ("c", "i"):
                break
        nota = ""
        while not nota:
            nota = input("nota (uma frase: o fato que decidiu): ").strip()
        i["rotulo_humano"] = "coerente" if r == "c" else "incoerente"
        i["rotulado_por"] = a.por
        i["nota_humana"] = nota
        i["origem_rotulo"] = "humano"
        with open(ARQ, "w", encoding="utf-8") as f:
            for x in itens:
                f.write(json.dumps(x, ensure_ascii=False) + "\n")
    feitos = sum(1 for x in itens if x.get("rotulo_humano"))
    print(f"\n{feitos}/{len(itens)} itens rotulados.")


if __name__ == "__main__":
    main()
