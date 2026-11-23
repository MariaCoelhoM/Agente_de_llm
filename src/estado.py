import operator
from typing import Annotated, List, Optional, TypedDict


class EstadoAtendimento(TypedDict, total=False):
    """Estado de UMA conversa (um thread_id). Cada mensagem do cliente é um
    turno: uma nova invocação do grafo sobre o mesmo checkpoint. Campos com
    reducer acumulam na conversa toda; os outros são substituídos."""

    thread_id: str
    contrato: str
    mensagem: str                 # a mensagem do turno corrente
    mensagem_inicial: str         # a primeira mensagem da conversa (vira o "sintoma" da memória)
    hoje: str
    turno: int                    # entrada: 1, 2, 3...

    # acumulam (reducer de soma / concatenação)
    mensagens: Annotated[List[dict], operator.add]     # conversa no formato do modelo, sem o system
    trajetoria: Annotated[List[dict], operator.add]    # o que aconteceu, para log, trace e memória
    tokens: Annotated[int, operator.add]
    tokens_entrada: Annotated[int, operator.add]
    tokens_saida: Annotated[int, operator.add]
    segundos_ativos: Annotated[float, operator.add]

    # substituem (um escritor cada)
    tokens_inicio_turno: int          # entrada: fotografia de `tokens` no início do turno
    segundos_inicio_turno: float      # entrada: idem para `segundos_ativos`
    memoria_contexto: str             # carregar_memoria
    rota: str                         # triagem
    voltas: int                       # agente (zerado pela entrada a cada turno)
    passos_ferramenta: int            # ferramentas (zerado pela entrada a cada turno)
    visita_proposta: Optional[dict]   # ferramentas escreve, agendar limpa
    decisao_humana: Optional[dict]    # aprovacao
    motivo_parada: Optional[str]      # quem encerra o turno
    resposta_texto: Optional[str]     # agente ou encaminhar_humano
    encerrada: bool                   # finalizar: conversa transferida para humano, não aceita mais turnos
    saida: Optional[dict]             # finalizar
