"""Remoção do titular, de ponta a ponta (P2 §5.4): grava, verifica que o
comportamento mudou, remove, verifica que voltou, e varre as estruturas
procurando o identificador. Usa bancos temporários e o modelo de regras.

Uso: python -m scripts.demo_remocao
"""
import os
import tempfile

from src import config, db, memoria
from src import observabilidade as obs
from src.chat import Conversa
from src.modelo_regras import ModeloRegras
from scripts.varrer_contrato import varrer

with tempfile.TemporaryDirectory() as pasta:
    db.DB_PATH = os.path.join(pasta, "provedor.db")
    config.CAMINHO_MEMORIA = os.path.join(pasta, "memoria.db")
    config.CAMINHO_CHECKPOINTS = os.path.join(pasta, "checkpoints.db")
    config.PASTA_LOGS = os.path.join(pasta, "logs")
    config.PASTA_TRACES = os.path.join(pasta, "traces")
    config.RAIZ = pasta  # a varredura olha só a pasta temporária
    obs.redirecionar(os.path.join(config.PASTA_TRACES, "demo.jsonl"))
    db.inicializar()
    hoje = db.conectar().execute("SELECT date('now')").fetchone()[0]

    print("1) antes: memória de C004 ->", repr(memoria.montar_contexto("C004", "sem internet", hoje)))
    c = Conversa(telefone="+5511900000004", llm=ModeloRegras())
    c.enviar("sem internet, luz vermelha")
    c.enviar("não")
    c.fechar()
    obs.descarregar()
    print("2) depois de um atendimento:", memoria.montar_contexto("C004", "sem internet", hoje).splitlines()[1:])
    print("   varredura:", len(varrer("C004")), "ocorrência(s)")
    print("3) remoção:", memoria.remover_titular("C004"))
    print("4) memória de C004 ->", repr(memoria.montar_contexto("C004", "sem internet", hoje)))
    achados = varrer("C004")
    print("5) varredura depois da remoção:", len(achados), "ocorrência(s)", achados)
    obs.redirecionar(None)
