import json
import os

from src import config, rag


def _perguntas():
    with open(os.path.join(config.PASTA_DADOS, "perguntas_rag.json"), encoding="utf-8") as f:
        return json.load(f)


def test_chunking_por_estrutura_cada_item_e_um_trecho():
    ids = [t.id for t in rag.carregar_trechos()]
    assert len(ids) == len(set(ids)) and {"S01", "P04", "E02", "V01"} <= set(ids)


def test_documento_revogado_fica_fora_do_indice_padrao():
    assert not any(t.doc.startswith("04_") for t in rag.construir_indice().trechos)
    assert any(t.doc.startswith("04_") for t in rag.construir_indice(incluir_revogados=True).trechos)


def test_acerto_em_3_nas_perguntas_com_resposta_no_corpus():
    indice = rag.construir_indice()
    for q in _perguntas():
        if not q["esperado_corpus"]:
            continue
        ids = [a["trecho"].id for a in indice.buscar(q["pergunta"], k=3)]
        assert set(q["esperado_corpus"]) & set(ids), q["id"]


def test_portao_barra_pergunta_fora_do_corpus():
    r = rag.consultar_base_conhecimento("quanto custa o plano de 500 mega")
    assert r["suficiente"] is False and r["trechos"] == []


def test_revogado_contamina_quando_incluido():
    limpo = rag.construir_indice().buscar("qual o prazo máximo para agendar a visita técnica", k=1)
    sujo = rag.construir_indice(incluir_revogados=True).buscar("qual o prazo máximo para agendar a visita técnica", k=1)
    assert limpo[0]["trecho"].id == "P04"
    assert sujo[0]["trecho"].doc.startswith("04_")