import os

from src import config, memoria

HOJE = "2026-10-18"


def test_gravar_fato_e_idempotente():
    a = memoria.gravar_fato("C001", "ultimo_sinal_dbm", "-22", HOJE, "testar_linha")
    b = memoria.gravar_fato("C001", "ultimo_sinal_dbm", "-22", HOJE, "testar_linha")
    assert a["ja_existia"] is False and b["ja_existia"] is True


def test_contradicao_vence_a_data_mais_recente_e_registra_descarte():
    memoria.gravar_fato("C001", "ultimo_sinal_dbm", "-22", "2026-09-01", "testar_linha")
    memoria.gravar_fato("C001", "ultimo_sinal_dbm", "-30", "2026-10-01", "testar_linha")
    assert memoria.fato_vigente("C001", "ultimo_sinal_dbm", HOJE)["valor"] == "-30"
    assert memoria.listar_descartes("C001")[0]["valor_descartado"] == "-22"


def test_fato_antigo_chegando_depois_nao_vence():
    memoria.gravar_fato("C001", "ultimo_sinal_dbm", "-30", "2026-10-01", "testar_linha")
    memoria.gravar_fato("C001", "ultimo_sinal_dbm", "-22", "2026-09-01", "testar_linha")
    assert memoria.fato_vigente("C001", "ultimo_sinal_dbm", HOJE)["valor"] == "-30"


def test_episodio_e_filtrado_por_contrato():
    memoria.registrar_episodio("C001", HOJE, "luz vermelha", "falha_fisica", "agendou_visita", "agendado")
    assert memoria.buscar_episodios("C002", "luz vermelha", HOJE) == []
    assert len(memoria.buscar_episodios("C001", "luz vermelha", HOJE)) == 1


def test_decaimento_rebaixa_sem_apagar():
    memoria.registrar_episodio("C001", "2026-01-01", "velho", "x", "y", "z")
    memoria.registrar_episodio("C001", HOJE, "novo", "x", "y", "z")
    assert memoria.aplicar_decaimento(HOJE) == 1
    assert [e["sintoma"] for e in memoria.buscar_episodios("C001", "x", HOJE)] == ["novo"]


def test_escrita_extraida_so_do_que_a_ferramenta_retornou():
    traj = [{"tipo": "ferramenta", "nome": "testar_linha", "args": {},
             "resultado": {"status": "OFFLINE", "sinal_dbm": -30.0, "falha_fisica_provavel": True}}]
    memoria.gravar_atendimento("C004", HOJE, "o cliente jura que o sinal é -10", traj)
    assert memoria.fato_vigente("C004", "ultimo_sinal_dbm", HOJE)["valor"] == "-30.0"


def test_remocao_apaga_em_todas_as_estruturas(tmp_path):
    import json, sqlite3
    memoria.gravar_fato("C001", "ultimo_sinal_dbm", "-22", HOJE, "testar_linha")
    memoria.registrar_episodio("C001", HOJE, "a", "b", "c", "d")
    os.makedirs(config.PASTA_LOGS)
    with open(os.path.join(config.PASTA_LOGS, "x.json"), "w") as f:
        json.dump({"contrato": "C001"}, f)
    conn = sqlite3.connect(config.CAMINHO_CHECKPOINTS)
    conn.execute("CREATE TABLE checkpoints (thread_id TEXT)")
    conn.execute("INSERT INTO checkpoints VALUES ('C001:abc')")
    conn.commit(); conn.close()
    r = memoria.remover_titular("C001")
    assert r["semantica"] == 1 and r["episodica"] == 1 and r["logs"] == 1 and r["checkpoints"] == 1
    assert memoria.fato_vigente("C001", "ultimo_sinal_dbm", HOJE) is None


def test_contexto_respeita_orcamento():
    for i in range(10):
        memoria.registrar_episodio("C001", f"2026-10-{i+1:02d}", "luz vermelha " + "x" * 80, "c", "a", "r")
    ctx = memoria.montar_contexto("C001", "luz vermelha", HOJE, orcamento_tokens=120)
    assert memoria.estimar_tokens(ctx) <= 120
