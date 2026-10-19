"""Fixtures compartilhadas: cada teste tem bancos próprios e data fixa.
Nenhum teste chama o modelo nem a rede."""
import datetime

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from src import config, db, tools

HOJE = datetime.date(2026, 10, 18)
AMANHA = (HOJE + datetime.timedelta(days=1)).isoformat()


@pytest.fixture(autouse=True)
def ambiente(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "provedor.db"))
    monkeypatch.setattr(config, "CAMINHO_MEMORIA", str(tmp_path / "memoria.db"))
    monkeypatch.setattr(config, "CAMINHO_CHECKPOINTS", str(tmp_path / "checkpoints.db"))
    monkeypatch.setattr(config, "PASTA_LOGS", str(tmp_path / "logs"))
    monkeypatch.setattr(tools, "_hoje", lambda: HOJE)
    db.inicializar()


@pytest.fixture
def checkpointer():
    return InMemorySaver()
