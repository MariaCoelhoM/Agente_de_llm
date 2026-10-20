"""
Gera docs/io.md a partir dos logs reais em logs/ (nada é escrito à mão:
os exemplos de entrada e saída são os dos logs, com commit e data).

Uso: python -m scripts.gerar_io
"""
import glob
import json
import os

from src import config

linhas = [
    "# Entrada e saída do sistema",
    "",
    "Exemplos reais, gerados por scripts/gerar_io.py a partir dos logs em logs/.",
    "A entrada é texto livre; o contrato vem da sessão e o thread_id é gerado pelo sistema.",
    "A saída é validada (src/schemas.py): resultado, fontes, suficiente.",
    "",
]
for caminho in sorted(glob.glob(os.path.join(config.PASTA_LOGS, "*.json"))):
    with open(caminho, encoding="utf-8") as f:
        log = json.load(f)
    if "commit" not in log:
        print(f"ignorado (formato antigo, anterior à Parte 2): {os.path.basename(caminho)}")
        continue
    s = log.get("saida") or {}
    ferramentas = [t["nome"] for t in log["trajetoria"] if t.get("tipo") == "ferramenta"]
    linhas += [
        f"## {os.path.basename(caminho)[:-5]}",
        "",
        f"- data: {log['timestamp']}, commit: {log['commit']}, modelo: {log['modelo']}, temperature: {log['temperature']}",
        f"- entrada: contrato {log['contrato']}, thread_id {log['thread_id']}, mensagem: \"{log['mensagem_inicial']}\"",
        f"- ferramentas chamadas: {', '.join(ferramentas) or 'nenhuma'}",
        f"- pausas de aprovação: {[(p['payload']['data_proposta'], p['resposta']) for p in log.get('pausas_de_aprovacao', [])] or 'nenhuma'}",
        f"- voltas: {log.get('voltas')}, tokens: {log.get('tokens')}, motivo de término: {log['motivo_parada']}",
        f"- saída: suficiente={s.get('suficiente')}, encaminhar_humano={s.get('encaminhar_humano')}, "
        f"fontes={[(f['tipo'], f['id']) for f in s.get('fontes', [])]}, citações inválidas={s.get('citacoes_invalidas')}",
        f"- resultado: {s.get('resultado')}",
        "",
    ]
destino = os.path.join(config.RAIZ, "docs", "io.md")
with open(destino, "w", encoding="utf-8") as f:
    f.write("\n".join(linhas))
print(f"{destino} gerado com {len(glob.glob(os.path.join(config.PASTA_LOGS, '*.json')))} logs")
