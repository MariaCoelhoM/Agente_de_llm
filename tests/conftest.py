"""Fixtures compartilhadas: cada teste tem bancos próprios e data fixa.
Nenhum teste chama o modelo nem a rede."""
import datetime

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from src import config, db, tools
from src import observabilidade as obs

HOJE = datetime.date(2026, 10, 18)
AMANHA = (HOJE + datetime.timedelta(days=1)).isoformat()


@pytest.fixture(autouse=True)
def ambiente(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "provedor.db"))
    monkeypatch.setattr(config, "CAMINHO_MEMORIA", str(tmp_path / "memoria.db"))
    monkeypatch.setattr(config, "CAMINHO_CHECKPOINTS", str(tmp_path / "checkpoints.db"))
    monkeypatch.setattr(config, "PASTA_LOGS", str(tmp_path / "logs"))
    monkeypatch.setattr(config, "ARQUIVO_SUSPENSAO", str(tmp_path / "SUSPENSO"))
    monkeypatch.setattr(tools, "_hoje", lambda: HOJE)
    obs.redirecionar(str(tmp_path / "traces.jsonl"))
    db.inicializar()
    yield
    obs.redirecionar(None)


@pytest.fixture
def checkpointer():
    return InMemorySaver()
