"""
Juiz LLM para UMA propriedade sem gabarito: a coerência da resposta final com
a trajetória (rubrica em evals/juiz/rubrica_coerencia.md). Critério binário,
saída estruturada validada por Pydantic.

Três usos:
  python -m evals.juiz --preparar <rodada> [<rodada> ...]   # monta evals/juiz/rotulos.jsonl (20 saídas)
  python -m evals.juiz --validar                            # juiz x rótulo humano: matriz e desacordos
  python -m evals.juiz --rodada <rodada>                    # julga os casos de uma rodada (se adotado)

O limiar de adoção foi declarado ANTES de medir (docs/evals.md §3):
concordância >= 85% E nenhum falso "coerente" (o juiz não pode deixar passar
uma resposta incoerente que o humano reprovou). Precisa do modelo real (.env).
"""
import argparse
import json
import os
import random
from typing import Literal

from pydantic import BaseModel, ValidationError

PASTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "juiz")
RUBRICA = os.path.join(PASTA, "rubrica_coerencia.md")
ROTULOS = os.path.join(PASTA, "rotulos.jsonl")
VALIDACAO = os.path.join(PASTA, "validacao.json")
LIMIAR = 85.0


class Veredito(BaseModel):
    veredito: Literal["coerente", "incoerente"]
    justificativa: str


def _versao_rubrica() -> str:
    for linha in open(RUBRICA, encoding="utf-8"):
        if linha.lower().startswith("versão:"):
            return linha.split(":", 1)[1].strip()
    return "?"


def resumir_trajetoria(trajetoria) -> str:
    linhas = []
    for t in trajetoria:
        if t.get("tipo") == "ferramenta":
            linhas.append(f"{t['nome']} -> {json.dumps(t['resultado'], ensure_ascii=False)[:300]}")
        elif t.get("tipo") == "aprovacao_humana":
            linhas.append(f"aprovação do cliente: {t.get('decisao')} -> {json.dumps(t.get('resultado'), ensure_ascii=False)}")
    return "\n".join(linhas) or "(nenhuma ferramenta chamada)"


def julgar(cliente: str, trajetoria_txt: str, resposta: str, cliente_llm=None) -> dict:
    from src.llm import ClienteLLM
    llm = cliente_llm or ClienteLLM()
    msgs = [{"role": "system", "content": open(RUBRICA, encoding="utf-8").read()},
            {"role": "user", "content": f"CLIENTE: {cliente}\n\nTRAJETÓRIA:\n{trajetoria_txt}\n\nRESPOSTA: {resposta}"}]
    r = llm._cliente().chat.completions.create(model=llm.modelo, messages=msgs, temperature=0,
                                               max_tokens=200, response_format={"type": "json_object"})
    try:
        return Veredito.model_validate_json(r.choices[0].message.content).model_dump()
    except ValidationError as erro:
        return {"veredito": "erro", "justificativa": str(erro)[:200]}


def preparar(rodadas):
    """Sorteia 20 saídas (semente fixa) das rodadas para rotulagem humana."""
    itens = []
    for pasta in rodadas:
        for c in map(json.loads, open(os.path.join(pasta, "casos.jsonl"), encoding="utf-8")):
            if not c.get("resposta_final"):
                continue
            itens.append({"id": f"{os.path.basename(pasta.rstrip('/'))}/{c['id']}",
                          "cliente": " | ".join(str(r["cliente"]) for r in c.get("respostas", [])),
                          "trajetoria": resumir_trajetoria(c.get("trajetoria", [])),
                          "resposta": c["resposta_final"],
                          "rotulo_humano": None, "rotulado_por": None, "nota_humana": ""})
    vistos, unicos = set(), []
    for i in itens:
        chave = (i["trajetoria"], i["resposta"])
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(i)
    random.Random(42).shuffle(unicos)
    with open(ROTULOS, "w", encoding="utf-8") as f:
        for i in unicos[:20]:
            f.write(json.dumps(i, ensure_ascii=False) + "\n")
    print(f"{min(20, len(unicos))} saídas em {ROTULOS}. Preencham rotulo_humano (coerente/incoerente), "
          "rotulado_por e nota_humana ANTES de rodar --validar.")


def validar():
    itens = [json.loads(l) for l in open(ROTULOS, encoding="utf-8") if l.strip()]
    faltam = [i["id"] for i in itens if i.get("rotulo_humano") not in ("coerente", "incoerente")]
    if faltam:
        raise SystemExit(f"{len(faltam)} itens sem rótulo humano: {faltam[:5]}... Rotulem antes de validar.")
    matriz = {"coerente": {"coerente": 0, "incoerente": 0}, "incoerente": {"coerente": 0, "incoerente": 0}}
    desacordos = []
    for i in itens:
        v = julgar(i["cliente"], i["trajetoria"], i["resposta"])
        i["juiz"] = v
        if v["veredito"] in ("coerente", "incoerente"):
            matriz[i["rotulo_humano"]][v["veredito"]] += 1
        if v["veredito"] != i["rotulo_humano"]:
            desacordos.append({"id": i["id"], "humano": i["rotulo_humano"], "juiz": v["veredito"],
                               "justificativa_juiz": v["justificativa"], "nota_humana": i.get("nota_humana"),
                               "classificacao": "PREENCHER: defeito do juiz | da rubrica | do rótulo humano"})
    acertos = matriz["coerente"]["coerente"] + matriz["incoerente"]["incoerente"]
    concordancia = round(100 * acertos / len(itens), 1)
    falso_coerente = matriz["incoerente"]["coerente"]
    resultado = {"versao_rubrica": _versao_rubrica(), "n": len(itens), "matriz_humano_x_juiz": matriz,
                 "concordancia": concordancia, "limiar": LIMIAR, "falsos_coerentes": falso_coerente,
                 "adotado": concordancia >= LIMIAR and falso_coerente == 0, "desacordos": desacordos}
    json.dump(resultado, open(VALIDACAO, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    with open(ROTULOS, "w", encoding="utf-8") as f:
        for i in itens:
            f.write(json.dumps(i, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in resultado.items() if k != "desacordos"}, ensure_ascii=False, indent=2))
    print(f"{len(desacordos)} desacordos em {VALIDACAO}: classifiquem cada um.")


def julgar_rodada(pasta):
    if not (os.path.exists(VALIDACAO) and json.load(open(VALIDACAO, encoding="utf-8"))["adotado"]):
        raise SystemExit("o juiz ainda não foi adotado (rode --validar e atinja o limiar)")
    saida = []
    for c in map(json.loads, open(os.path.join(pasta, "casos.jsonl"), encoding="utf-8")):
        if c.get("resposta_final"):
            v = julgar(" | ".join(str(r["cliente"]) for r in c["respostas"]),
                       resumir_trajetoria(c["trajetoria"]), c["resposta_final"])
            saida.append({"id": c["id"], **v})
    with open(os.path.join(pasta, "juiz.jsonl"), "w", encoding="utf-8") as f:
        for s in saida:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    ok = sum(s["veredito"] == "coerente" for s in saida)
    print(f"coerentes: {ok}/{len(saida)}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--preparar", nargs="+")
    p.add_argument("--validar", action="store_true")
    p.add_argument("--rodada")
    a = p.parse_args()
    if a.preparar:
        preparar(a.preparar)
    elif a.validar:
        validar()
    elif a.rodada:
        julgar_rodada(a.rodada)
    else:
        p.print_help()
