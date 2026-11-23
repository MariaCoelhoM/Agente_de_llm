import datetime
import json
from typing import List, Optional

from . import config

# motivo -> (descrição, encaminha para humano?)
MOTIVOS = {
    "resposta_final": ("o modelo respondeu sem pedir mais ferramentas", False),
    "encaminhado_humano": ("assunto fora do suporte técnico, decidido pela triagem", True),
    "entrada_incompleta": ("a mensagem não descreve nenhum sintoma; o sistema pede detalhes sem chamar o modelo", False),
    "limite_de_voltas": (f"mais de {config.MAX_VOLTAS_AGENTE} chamadas ao modelo", True),
    "limite_de_ferramentas": (f"mais de {config.MAX_PASSOS_FERRAMENTA} chamadas de ferramenta", True),
    "laco_detectado": (f"mesma ferramenta e mesmos argumentos {config.REPETICOES_PARA_LACO} vezes sem mudança no estado", True),
    "tempo_esgotado": (f"mais de {config.TETO_SEGUNDOS}s de tempo de máquina", True),
    "tokens_esgotados": (f"mais de {config.TETO_TOKENS} tokens", True),
    "aprovacao_expirada": ("o cliente não respondeu à aprovação no prazo", True),
    "erro_fatal_llm": ("erro do modelo que repetir não resolve", True),
    "recursion_limit": (f"o grafo passou de {config.RECURSION_LIMIT} passos", True),
    # Parte 3
    "aguardando_humano": ("o turno parou no ponto de aprovação e espera a resposta do cliente", False),
    "conversa_longa": (f"mais de {config.MAX_TURNOS_CONVERSA} mensagens do cliente ou {config.TETO_TOKENS_CONVERSA} tokens na conversa", True),
    "agente_suspenso": ("o agente foi suspenso pela operação (kill switch); nada é executado", True),
    "ferramenta_indisponivel": ("uma ferramenta levantou exceção (banco travado, por exemplo); o turno para sem repetir a escrita", True),
}

FERRAMENTAS_DE_ESCRITA = {"reiniciar_conexao"}


def verificar_orcamento(estado: dict) -> Optional[str]:
    """Tetos por TURNO (voltas, tokens e tempo gastos desde a última mensagem
    do cliente) e um teto da conversa inteira (tokens somados). `tokens` e
    `segundos_ativos` acumulam na conversa toda (reducer de soma); o início do
    turno é gravado pelo nó `entrada`."""
    tokens_turno = estado.get("tokens", 0) - estado.get("tokens_inicio_turno", 0)
    segundos_turno = estado.get("segundos_ativos", 0.0) - estado.get("segundos_inicio_turno", 0.0)
    if estado.get("voltas", 0) >= config.MAX_VOLTAS_AGENTE:
        return "limite_de_voltas"
    if tokens_turno >= config.TETO_TOKENS:
        return "tokens_esgotados"
    if segundos_turno >= config.TETO_SEGUNDOS:
        return "tempo_esgotado"
    if estado.get("tokens", 0) >= config.TETO_TOKENS_CONVERSA:
        return "conversa_longa"
    return None


def _chave(nome: str, args: dict) -> str:
    return nome + json.dumps(args, sort_keys=True, ensure_ascii=False)


def detectar_laco(trajetoria: List[dict], nome: str, args: dict) -> bool:
    """Conta repetições idênticas dentro do turno corrente, desde a última
    escrita DIFERENTE da chamada atual. Repetir uma leitura depois de uma
    escrita é legítimo (testar de novo depois de reiniciar); repetir sem nada
    ter mudado é laço. Correção da Parte 3: antes, uma escrita repetida
    (reiniciar, reiniciar, reiniciar) zerava a própria contagem e nunca era
    detectada. Um turno novo do cliente também zera: pedir "testa de novo"
    em outra mensagem é legítimo."""
    alvo = _chave(nome, args)
    repeticoes = 1
    for item in reversed(trajetoria):
        if item.get("tipo") == "turno":
            break
        if item.get("tipo") != "ferramenta":
            continue
        if _chave(item["nome"], item.get("args", {})) == alvo:
            repeticoes += 1
        elif item["nome"] in FERRAMENTAS_DE_ESCRITA:
            break
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


def agente_suspenso() -> bool:
    """Kill switch (§2.2 da Parte 3): a existência do arquivo dados/SUSPENSO
    suspende o agente. Quem pode criar o arquivo: quem opera a máquina (o
    responsável técnico). Fail-closed: se não der para verificar, suspende."""
    import os
    try:
        return os.path.exists(config.ARQUIVO_SUSPENSAO)
    except OSError:
        return True
