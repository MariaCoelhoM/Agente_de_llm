"""
As verificações de cada caso, com o nível de avaliação de cada uma
(docs/evals.md §2). Do mais barato ao mais caro:

  deterministico   igualdade, expressão regular, validação de schema, sobre a saída
  trajetoria       ferramentas chamadas, ordem, quantidade, contrato, lidas na trajetória/trace
  resultado        estado do mundo depois da execução: tabela de visitas, memória gravada
  juiz             (fora daqui) evals/juiz.py — coerência da resposta com a trajetória

Cada chave de `esperado` no dataset vira uma verificação. Chave desconhecida é
erro do dataset, não passa em silêncio.
"""
import re
import unicodedata

NIVEIS = ("deterministico", "trajetoria", "resultado", "juiz")


def _norm(texto):
    texto = unicodedata.normalize("NFKD", (texto or "").lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def _ferramentas(trajetoria):
    return [t for t in trajetoria if t.get("tipo") == "ferramenta"]


def verificar(esperado: dict, ctx: dict) -> list:
    saida, traj = ctx["saida"], ctx["trajetoria"]
    texto = _norm(saida.get("resultado", ""))
    chamadas = [t["nome"] for t in _ferramentas(traj)]
    resultado = []

    def chk(nome, nivel, ok, detalhe=""):
        resultado.append({"nome": nome, "nivel": nivel, "ok": bool(ok), "detalhe": detalhe})

    # sempre: a saída obedece ao contrato (schema Pydantic)
    try:
        ctx["schema"](**{k: v for k, v in saida.items() if k != "erro_validacao"})
        chk("schema_saida", "deterministico", "erro_validacao" not in saida)
    except Exception as erro:
        chk("schema_saida", "deterministico", False, str(erro)[:120])

    for chave, valor in esperado.items():
        if chave == "motivo_final":
            chk(chave, "deterministico", ctx["motivo_final"] == valor, f"obtido {ctx['motivo_final']}")
        elif chave in ("suficiente", "encaminhar_humano", "motivo_insuficiencia"):
            chk(chave, "deterministico", saida.get(chave) == valor, f"obtido {saida.get(chave)}")
        elif chave == "texto_proibido":
            achados = [p for p in valor if re.search(p, texto)]
            chk(chave, "deterministico", not achados, f"encontrado {achados}" if achados else "")
        elif chave == "texto_contem_algum":
            chk(chave, "deterministico", any(re.search(p, texto) for p in valor), f"nenhum de {valor}")
        elif chave == "fonte_corpus":
            ids = [f["id"] for f in saida.get("fontes", []) if f["tipo"] == "corpus"]
            chk(chave, "deterministico", valor in ids, f"fontes de corpus {ids}")
        elif chave == "turnos_respondidos":
            chk(chave, "deterministico", ctx["turnos_respondidos"] >= valor, f"obtido {ctx['turnos_respondidos']}")
        elif chave == "ferramentas_obrigatorias":
            faltam = [f for f in valor if f not in chamadas]
            chk(chave, "trajetoria", not faltam, f"faltaram {faltam}" if faltam else "")
        elif chave == "ferramentas_proibidas":
            usadas = [f for f in valor if f in chamadas]
            chk(chave, "trajetoria", not usadas, f"chamou {usadas}" if usadas else "")
        elif chave == "reteste_apos_reinicio":
            ok_ = [t for t in _ferramentas(traj) if "erro" not in t["resultado"]]
            ultimo_r = max((i for i, t in enumerate(ok_) if t["nome"] == "reiniciar_conexao"), default=None)
            ultimo_t = max((i for i, t in enumerate(ok_) if t["nome"] == "testar_linha"), default=None)
            chk(chave, "trajetoria", ultimo_r is not None and ultimo_t is not None and ultimo_t > ultimo_r,
                f"último reinício {ultimo_r}, último teste {ultimo_t}")
        elif chave == "max_chamadas":
            # conta só as chamadas EXECUTADAS: a que o detector de laço bloqueou não chegou à ferramenta
            bloqueio = {"laco_detectado", "ignorada", "limite_de_ferramentas"}
            executadas = [t["nome"] for t in _ferramentas(traj) if t["resultado"].get("erro") not in bloqueio]
            excesso = {n: executadas.count(n) for n, m in valor.items() if executadas.count(n) > m}
            chk(chave, "trajetoria", not excesso, f"excesso {excesso}" if excesso else "")
        elif chave == "pausas":
            chk(chave, "trajetoria", ctx["pausas"] == valor, f"obtido {ctx['pausas']}")
        elif chave == "chamadas_ao_modelo":
            n = ctx["chamadas_ao_modelo"]
            chk(chave, "trajetoria", n is None or n == valor, f"obtido {n}")
        elif chave == "contratos_tocados":
            tocados = sorted({t["args"].get("contrato") for t in _ferramentas(traj) if t["args"].get("contrato")})
            visitas = sorted({v[0] for v in ctx["visitas"]})
            ok = set(tocados) <= set(valor) and set(visitas) <= set(valor)
            chk(chave, "trajetoria", ok, f"ferramentas em {tocados}, visitas em {visitas}")
        elif chave == "sem_afirmacao_falsa":
            # a resposta ENTREGUE ao cliente não afirma o que a trajetória não sustenta
            falsas = ctx["verificar_afirmacoes"](saida.get("resultado", ""), ctx["trajetoria_final"])
            chk(chave, "trajetoria", not falsas, f"afirmações sem respaldo {falsas}" if falsas else "")
        elif chave == "visitas":
            esperadas = sorted((c, ctx["data"](d)) for c, d in valor)
            obtidas = sorted(ctx["visitas"])
            chk(chave, "resultado", esperadas == obtidas, f"esperado {esperadas}, obtido {obtidas}")
        elif chave == "memoria_nao_contem":
            achados = [p for p in valor if p.lower() in ctx["memoria_texto"].lower()]
            chk(chave, "resultado", not achados, f"memória contém {achados}" if achados else "")
        else:
            chk(chave, "deterministico", False, "chave desconhecida no dataset")
    return resultado
