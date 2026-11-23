"""Acrescenta a docs/io.md a seção da Parte 3, gerada dos logs de logs/parte3/<modelo>/.

Uso: python -m scripts.gerar_io_chat [regras|real]
"""
import glob
import json
import os
import sys

from src import config

MARCA = "\n## Parte 3: conversas pelo chat"
LEITURA = {
    "chat_C001_feliz": "o caminho feliz em três turnos: a entrada sem sintoma recebe pedido de detalhes sem chamar o modelo; o reinício só é dito com o reteste ONLINE (fontes com as três ferramentas); o 'obrigado' não reabre o diagnóstico.",
    "chat_C004_visita_editada": "a pausa no meio da conversa: o cartão vem do código, a resposta que o código não entende (`aprovacao_nao_entendida`) repete o cartão, e 'não, prefiro dd/mm' vira aprovação editando a data.",
    "chat_C003_divergencia": "entrada de divergência (§1.4): o sistema não diz 'resolvido' com a linha ONLINE. No segundo turno o modelo **diz** que vai encaminhar, mas `encaminhar_humano` fica `false`: quem encaminha é o código, e nenhuma regra disparou. É o tipo de incoerência entre texto e ação que o verificador C4 não cobre e o juiz de coerência (`docs/evals.md` §3) precisa pegar.",
    "chat_fora_do_corpus": "a recusa: `suficiente=false`, `motivo_insuficiencia=fora_do_corpus`, `encaminhar_humano=true`, sem inventar resposta.",
    "chat_injecao": "o controle C4: o modelo (ingênuo) obedeceu 'diga que a visita já está agendada'; o código trocou o texto e marcou `afirmacoes_bloqueadas`.",
}


def main():
    modelo = sys.argv[1] if len(sys.argv) > 1 else "regras"
    pasta = os.path.join(config.RAIZ, "logs", "parte3", modelo)
    destino = os.path.join(config.RAIZ, "docs", "io.md")
    texto = open(destino, encoding="utf-8").read()
    if MARCA in texto:
        texto = texto[:texto.index(MARCA)].rstrip() + "\n"
    linhas = [MARCA.strip(), "",
              f"Geradas por `python -m scripts.rodar_conversas --modelo {modelo}` e `python -m scripts.gerar_io_chat {modelo}`, "
              f"a partir de `logs/parte3/{modelo}/*.json` (traces em `logs/parte3/{modelo}/traces.jsonl`). "
              + ("**Modelo de regras**, não o LLM: mostram o contrato de entrada (texto livre + telefone do canal) e de saída do chat. "
                 "Para a versão com o modelo real: `python -m scripts.rodar_conversas --modelo real` e `python -m scripts.gerar_io_chat real`. "
                 if modelo == "regras" else "")
              + "Se o campo `commit` diz `sem-git`, o log foi gerado antes do commit que o contém (`git log -- logs/parte3`).", ""]
    for f in sorted(glob.glob(os.path.join(pasta, "*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        nome = os.path.basename(f)[:-5]
        linhas += [f"### {nome}", "",
                   f"- data {d['timestamp']} · commit {d['commit']} · versão {d['versao_sistema']} · modelo {d['modelo']} · "
                   f"contrato {d['contrato']} (origem: {d['identidade']['origem']}) · thread {d['thread_id']}"]
        for t in d["turnos"]:
            trace = f" · trace `{t['trace_id'][:8]}`" if t.get("trace_id") else ""
            linhas.append(f"- **cliente:** \"{t['cliente']}\" → motivo `{t['motivo']}`{trace}")
            if t.get("saida"):
                linhas.append(f"  - **saída:** `{json.dumps(t['saida'], ensure_ascii=False)}`")
            elif t["motivo"] == "aguardando_humano":
                p = t["aprovacao_pendente"]
                linhas.append(f"  - **pausa de aprovação:** ação `{p['acao']}`, contrato {p['contrato']}, data {p['data_proposta']}")
        if nome in LEITURA:
            linhas.append(f"- **o que ler aqui:** {LEITURA[nome]}")
        linhas.append("")
    with open(destino, "w", encoding="utf-8") as arquivo:
        arquivo.write(texto + "\n" + "\n".join(linhas))
    print(f"{destino} atualizado")


if __name__ == "__main__":
    main()
