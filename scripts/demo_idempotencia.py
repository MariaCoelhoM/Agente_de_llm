import os
import tempfile

from src import db, tools

with tempfile.TemporaryDirectory() as pasta:
    db.DB_PATH = os.path.join(pasta, "demo.db")
    db.inicializar()
    amanha = tools.obter_data_atual()["amanha"]
    for n in (1, 2):
        print(f"aprovação {n}:", tools.agendar_visita_tecnico("C004", amanha, True))
    conn = db.conectar()
    print("linhas em visitas:", conn.execute("SELECT COUNT(*) FROM visitas").fetchone()[0])
    conn.close()