"""Retenção (docs/model-card.md, Registro e retenção): logs de execução e
traces locais com mais de 30 dias são apagados. Os traces e logs CITADOS como
evidência (logs/parte2/, logs/parte3/, evals/resultados/) são de dados
sintéticos e ficam no git; esta rotina não os toca.

  python -m scripts.limpar_logs_antigos --simular
  python -m scripts.limpar_logs_antigos
"""
import argparse
import os
import time

from src import config

DIAS = 30


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--simular", action="store_true")
    a = p.parse_args()
    limite = time.time() - DIAS * 86400
    apagados = 0
    for pasta in (config.PASTA_LOGS, config.PASTA_TRACES):
        if not os.path.isdir(pasta):
            continue
        for nome in os.listdir(pasta):
            caminho = os.path.join(pasta, nome)
            if os.path.isfile(caminho) and os.path.getmtime(caminho) < limite:
                print(("apagaria " if a.simular else "apagado ") + caminho)
                if not a.simular:
                    os.remove(caminho)
                apagados += 1
    print(f"{apagados} arquivo(s) com mais de {DIAS} dias")


if __name__ == "__main__":
    main()
