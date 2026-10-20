import os
import sqlite3
import sys

from src import config


def varrer(contrato: str):
    achados = []
    for pasta, _, arquivos in os.walk(config.RAIZ):
        if any(p in pasta for p in (".git", "venv", ".venv", "__pycache__", "node_modules")):
            continue
        for nome in arquivos:
            caminho = os.path.join(pasta, nome)
            if nome == "provedor.db":
                continue  # fonte de verdade do provedor, fora da memória do agente
            if nome.endswith(".db"):
                conn = sqlite3.connect(caminho)
                for (tabela,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'"):
                    colunas = [c[1] for c in conn.execute(f"PRAGMA table_info({tabela})")]
                    for coluna in colunas:
                        n = conn.execute(f"SELECT COUNT(*) FROM {tabela} WHERE CAST({coluna} AS TEXT) LIKE ?",
                                         (f"%{contrato}%",)).fetchone()[0]
                        if n:
                            achados.append(f"{caminho}: {tabela}.{coluna} ({n})")
                conn.close()
            elif nome.endswith((".json", ".md", ".txt")) and "tests" not in pasta and "docs" not in pasta:
                try:
                    if contrato in open(caminho, encoding="utf-8").read():
                        achados.append(caminho)
                except (OSError, UnicodeDecodeError):
                    pass
    return achados


if __name__ == "__main__":
    contrato = sys.argv[1]
    achados = varrer(contrato)
    print(f"{contrato}: {len(achados)} ocorrência(s)")
    for a in achados:
        print("  ", a)
    sys.exit(1 if achados else 0)