"""
Regra da frase (enunciado §2.3): tira UMA frase do prompt e compara o
comportamento com e sem ela, no mesmo caso, N vezes, com o modelo real.

A frase testada é a que obriga a testar a linha de novo depois de reiniciar a
conexão. Métrica objetiva, lida da trajetória: depois de reiniciar_conexao,
houve um testar_linha antes da resposta final? Cada execução usa bancos
temporários, então os dados de dados/ não são tocados e a memória de uma
execução não contamina a seguinte.

Uso: python -m scripts.experimento_frase [N]     (padrão N=5; precisa de .env e rede)
Escreve docs/experimento_frase.md.
"""
import datetime
import os
import sys
import tempfile

from src import config, db
from src.agent import decisor_fixo, executar_atendimento

FRASE = "- Nunca diga que resolveu sem rodar testar_linha de novo depois de reiniciar_conexao.\n"
CASO = ("C001", "A luz do modem está piscando vermelha e a internet caiu.")


def retestou(trajetoria):
    nomes = [t["nome"] for t in trajetoria if t.get("tipo") == "ferramenta"]
    if "reiniciar_conexao" not in nomes:
        return None  # não reiniciou: a pergunta não se aplica
    depois = nomes[len(nomes) - 1 - nomes[::-1].index("reiniciar_conexao") + 1:]
    return "testar_linha" in depois


def rodar(variante, n):
    resultados = []
    for i in range(n):
        with tempfile.TemporaryDirectory() as pasta:
            db.DB_PATH = os.path.join(pasta, "provedor.db")
            config.CAMINHO_MEMORIA = os.path.join(pasta, "memoria.db")
            config.CAMINHO_CHECKPOINTS = os.path.join(pasta, "checkpoints.db")
            config.PASTA_LOGS = os.path.join(pasta, "logs")
            db.inicializar()
            r = executar_atendimento(CASO[0], CASO[1], decisor=decisor_fixo("rejeitar"),
                                     rotulo=f"experimento_{variante}_{i}")
            resultados.append((retestou(r["trajetoria"]), r["saida"]["resultado"]))
    return resultados


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    original = os.path.join(config.PASTA_PROMPTS, config.PROMPT_SISTEMA)
    texto = open(original, encoding="utf-8").read()
    if FRASE not in texto:
        sys.exit("a frase não foi encontrada no prompt; atualize FRASE em scripts/experimento_frase.py")
    variante_nome = "suporte_v2_sem_frase.md"
    variante = os.path.join(config.PASTA_PROMPTS, variante_nome)
    with open(variante, "w", encoding="utf-8") as f:
        f.write(texto.replace(FRASE, ""))
    try:
        com = rodar("com", n)
        config.PROMPT_SISTEMA = variante_nome
        sem = rodar("sem", n)
    finally:
        config.PROMPT_SISTEMA = os.path.basename(original)
        os.remove(variante)

    def resumo(lista):
        aplicaveis = [x for x in lista if x[0] is not None]
        return len(aplicaveis), sum(1 for x in aplicaveis if x[0])

    ca, cs = resumo(com)
    sa, ss = resumo(sem)
    linhas = [
        "# Experimento da frase",
        "",
        f"Gerado por scripts/experimento_frase.py em {datetime.datetime.now().isoformat(timespec='seconds')}, modelo {config.MODELO}, temperature {config.TEMPERATURE}.",
        "",
        f"Frase removida: `{FRASE.strip()}`",
        f"Caso: contrato {CASO[0]}, mensagem \"{CASO[1]}\", {n} execuções por variante, bancos temporários.",
        "Métrica (lida da trajetória): depois de reiniciar_conexao, o agente rodou testar_linha antes de responder?",
        "",
        "| Variante | Execuções em que reiniciou | Rodou testar_linha depois |",
        "|---|---|---|",
        f"| com a frase | {ca} de {n} | {cs} |",
        f"| sem a frase | {sa} de {n} | {ss} |",
        "",
        "Respostas finais (variante sem a frase):",
        "",
    ]
    linhas += [f"- retestou={r[0]}: {r[1]}" for r in sem]
    linhas += ["", "Leitura: se a coluna da variante sem a frase cair, a frase carrega comportamento; se não cair, ela é redundante com a descrição das ferramentas e pode sair do prompt.", ""]
    destino = os.path.join(config.RAIZ, "docs", "experimento_frase.md")
    with open(destino, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))
    print(f"{destino} gerado\ncom a frase: {cs}/{ca}   sem a frase: {ss}/{sa}")


if __name__ == "__main__":
    main()
