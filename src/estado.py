import operator
from typing import Annotated, List, Optional, TypedDict


class EstadoAtendimento(TypedDict, total=False):
    thread_id: str
    contrato: str
    mensagem: str
    hoje: str

    mensagens: Annotated[List[dict], operator.add]     # conversa no formato do modelo, sem o system
    trajetoria: Annotated[List[dict], operator.add]    # o que aconteceu, para log e memória
    tokens: Annotated[int, operator.add]               
    segundos_ativos: Annotated[float, operator.add]    

    # substituem (um escritor cada)
    memoria_contexto: str       # carregar_memoria
    rota: str                   # triagem
    voltas: int                 # agente
    passos_ferramenta: int      # ferramentas
    visita_proposta: Optional[dict]   # ferramentas escreve, agendar limpa
    decisao_humana: Optional[dict]    # aprovacao
    motivo_parada: Optional[str]      # quem encerra
    resposta_texto: Optional[str]     # agente ou encaminhar_humano
    saida: Optional[dict]             # finalizar
