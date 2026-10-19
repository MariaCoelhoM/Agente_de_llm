import pytest

from src import config, db, tools

from .conftest import AMANHA


def test_agendar_exige_confirmacao_explicita():
    assert tools.agendar_visita_tecnico("C004", AMANHA, False)["erro"] == "confirmacao_do_cliente_necessaria"


def test_nao_agenda_em_bairro_em_manutencao():
    assert tools.agendar_visita_tecnico("C005", AMANHA, True)["erro"] == "bairro_em_manutencao_nao_agendar_individual"


def test_agenda_em_bairro_sem_manutencao():
    r = tools.agendar_visita_tecnico("C004", AMANHA, True)
    assert r["status"] == "AGENDADA" and r["ja_existia"] is False


def test_agendar_e_idempotente():
    tools.agendar_visita_tecnico("C004", AMANHA, True)
    r = tools.agendar_visita_tecnico("C004", AMANHA, True)
    assert r["ja_existia"] is True
    conn = db.conectar()
    assert conn.execute("SELECT COUNT(*) FROM visitas").fetchone()[0] == 1
    conn.close()


@pytest.mark.parametrize("data", ["ontem", "2026-10-17", "2027-01-01", ""])
def test_agendar_recusa_data_invalida_ou_fora_da_janela(data):
    assert "erro" in tools.agendar_visita_tecnico("C004", data, True)


def test_propor_aceita_so_hoje_ou_amanha():
    assert tools.propor_visita("C004", AMANHA)["proposta"] is True
    assert tools.propor_visita("C004", "2026-10-25")["erro"] == "data_fora_da_janela"


@pytest.mark.parametrize("nome", ["testar_linha", "conferir_queda_bairro", "reiniciar_conexao"])
def test_contrato_inexistente_e_erro_como_dado(nome):
    assert tools.FUNCOES[nome]("C999")["erro"] == "contrato_nao_encontrado"


def test_agendar_contrato_inexistente():
    assert tools.agendar_visita_tecnico("C999", AMANHA, True)["erro"] == "contrato_nao_encontrado"


def test_reiniciar_recusa_falha_fisica():
    assert tools.reiniciar_conexao("C004")["erro"] == "falha_fisica_reinicio_nao_resolve"


def test_banco_antigo_e_migrado(tmp_path, monkeypatch):
    """Banco criado antes da Parte 2 (sem coluna chave) ganha a coluna e o índice."""
    import sqlite3
    caminho = str(tmp_path / "antigo.db")
    conn = sqlite3.connect(caminho)
    conn.execute("CREATE TABLE visitas (id INTEGER PRIMARY KEY AUTOINCREMENT, contrato TEXT, data TEXT, status TEXT)")
    conn.execute("INSERT INTO visitas (contrato, data, status) VALUES ('C001','2026-10-19','AGENDADA')")
    conn.commit(); conn.close()
    monkeypatch.setattr(db, "DB_PATH", caminho)
    db.inicializar()
    c = db.conectar()
    assert c.execute("SELECT chave FROM visitas").fetchone()[0] == db.chave_visita("C001", "2026-10-19")
    c.close()