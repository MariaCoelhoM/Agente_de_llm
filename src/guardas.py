import datetime
import json
from typing import List, Optional

from . import config

# motivo -> (descrição, encaminha para humano)
MOTIVOS = {
    "resposta_final": ("o modelo respondeu sem pedir mais ferramentas", False),
    "encaminhado_humano": ("assunto fora do suporte técnico, decidido pela triagem", True),
    "limite_de_voltas": (f"mais de {config.MAX_VOLTAS_AGENTE} chamadas ao modelo", True),
    "limite_de_ferramentas": (f"mais de {config.MAX_PASSOS_FERRAMENTA} chamadas de ferramenta", True),
    "laco_detectado": (f"mesma ferramenta e mesmos argumentos {config.REPETICOES_PARA_LACO} vezes sem mudança no estado", True),
    "tempo_esgotado": (f"mais de {config.TETO_SEGUNDOS}s de tempo de máquina", True),
    "tokens_esgotados": (f"mais de {config.TETO_TOKENS} tokens", True),
    "aprovacao_expirada": ("o cliente não respondeu à aprovação no prazo", True),
    "erro_fatal_llm": ("erro do modelo que repetir não resolve", True),
    "recursion_limit": (f"o grafo passou de {config.RECURSION_LIMIT} passos", True),
}

FERRAMENTAS_DE_ESCRITA = {"reiniciar_conexao"}


def verificar_orcamento(estado: dict) -> Optional[str]:
    if estado.get("voltas", 0) >= config.MAX_VOLTAS_AGENTE:
        return "limite_de_voltas"
    if estado.get("tokens", 0) >= config.TETO_TOKENS:
        return "tokens_esgotados"
    if estado.get("segundos_ativos", 0.0) >= config.TETO_SEGUNDOS:
        return "tempo_esgotado"
    return None


def _chave(nome: str, args: dict) -> str:
    return nome + json.dumps(args, sort_keys=True, ensure_ascii=False)


def detectar_laco(trajetoria: List[dict], nome: str, args: dict) -> bool:
    """Conta repetições idênticas desde a última escrita. Repetir uma leitura
    depois de uma escrita é legítimo (testar de novo depois de reiniciar);
    repetir sem nada ter mudado é laço."""
    repeticoes = 1
    for item in reversed(trajetoria):
        if item.get("tipo") != "ferramenta":
            continue
        if item["nome"] in FERRAMENTAS_DE_ESCRITA:
            break
        if _chave(item["nome"], item.get("args", {})) == _chave(nome, args):
            repeticoes += 1
    return repeticoes >= config.REPETICOES_PARA_LACO


def validar_data_edicao(data: str, hoje: str) -> Optional[str]:
    """Edição do cliente: entre hoje e hoje + DIAS_MAXIMOS_VISITA."""
    try:
        alvo = datetime.date.fromisoformat(data)
    except (TypeError, ValueError):
        return "formato_invalido"
    base = datetime.date.fromisoformat(hoje)
    if alvo < base:
        return "data_no_passado"
    if alvo > base + datetime.timedelta(days=config.DIAS_MAXIMOS_VISITA):
        return "alem_da_janela"
    return None
