"""
Ferramentas do agente. Cada função retorna um dict (nunca lança exceção para
fora): erro de ferramenta é dado que o modelo lê e usa para se corrigir
(requisito 4.1 — "erro de ferramenta como dado").
"""
import datetime

from . import config, db, rag


def _hoje() -> datetime.date:
    """Único ponto de leitura do relógio. Os testes substituem esta função
    para não dependerem do dia em que rodam."""
    return datetime.date.today()


def obter_data_atual() -> dict:
    """Leitura, sem argumentos. O modelo não tem relógio; chama isso sempre
    que precisar saber a data de hoje, por exemplo antes de propor uma
    visita técnica para o dia seguinte (regra do domínio, case §2.1)."""
    hoje = _hoje()
    amanha = hoje + datetime.timedelta(days=1)
    return {"hoje": hoje.isoformat(), "amanha": amanha.isoformat()}


def testar_linha(contrato: str) -> dict:
    """Leitura. Não altera nada."""
    conn = db.conectar()
    row = conn.execute(
        "SELECT * FROM modems WHERE contrato = ?", (contrato,)
    ).fetchone()
    conn.close()
    if row is None:
        return {"erro": "contrato_nao_encontrado", "contrato": contrato}
    return {
        "contrato": contrato,
        "status": row["status"],
        "sinal_dbm": row["sinal_dbm"],
        "falha_fisica_provavel": row["sinal_dbm"] <= -27,
    }


def conferir_queda_bairro(contrato: str) -> dict:
    """Leitura. Descobre o bairro do cliente pelo contrato e verifica
    manutenção — não pede o bairro como argumento porque o modelo não tem
    esse dado em lugar nenhum da conversa; só o sistema do provedor sabe."""
    conn = db.conectar()
    cliente = conn.execute(
        "SELECT bairro FROM clientes WHERE contrato = ?", (contrato,)
    ).fetchone()
    if cliente is None:
        conn.close()
        return {"erro": "contrato_nao_encontrado", "contrato": contrato}
    row = conn.execute(
        "SELECT * FROM bairros WHERE nome = ?", (cliente["bairro"],)
    ).fetchone()
    conn.close()
    if row is None:
        return {"erro": "bairro_nao_encontrado", "bairro": cliente["bairro"]}
    return {"bairro": cliente["bairro"], "em_manutencao": bool(row["em_manutencao"])}


def reiniciar_conexao(contrato: str) -> dict:
    """Escrita reversível. O limite de 3 por atendimento é controlado pelo
    laço do agente (estado da conversa), não aqui."""
    conn = db.conectar()
    row = conn.execute(
        "SELECT * FROM modems WHERE contrato = ?", (contrato,)
    ).fetchone()
    if row is None:
        conn.close()
        return {"erro": "contrato_nao_encontrado", "contrato": contrato}
    if row["sinal_dbm"] <= -27:
        conn.close()
        return {
            "erro": "falha_fisica_reinicio_nao_resolve",
            "sinal_dbm": row["sinal_dbm"],
        }
    conn.execute(
        "UPDATE modems SET status = 'ONLINE', reinicios_hoje = reinicios_hoje + 1 "
        "WHERE contrato = ?",
        (contrato,),
    )
    conn.commit()
    conn.close()
    return {"contrato": contrato, "status": "ONLINE"}


chave_visita = db.chave_visita


def validar_data(data: str, ate_dias: int) -> dict:
    """Valida formato e janela [hoje, hoje + ate_dias]. Devolve erro como dado."""
    try:
        alvo = datetime.date.fromisoformat(data)
    except (TypeError, ValueError):
        return {"erro": "data_invalida", "esperado": "AAAA-MM-DD"}
    hoje = _hoje()
    if alvo < hoje or alvo > hoje + datetime.timedelta(days=ate_dias):
        return {"erro": "data_fora_da_janela", "de": hoje.isoformat(),
                "ate": (hoje + datetime.timedelta(days=ate_dias)).isoformat()}
    return {}


def propor_visita(contrato: str, data: str) -> dict:
    """Validação pura: não escreve nada. É a única porta do modelo para a
    visita técnica. A proposta só vira agendamento depois que uma pessoa
    responde ao interrupt do grafo (src/grafo.py, nó `aprovacao`). A data
    proposta pelo agente vai até amanhã (case §2.1); só o cliente pode
    escolher uma data posterior."""
    erro = validar_data(data, ate_dias=1)
    if erro:
        return erro
    conn = db.conectar()
    cliente = conn.execute(
        "SELECT bairro FROM clientes WHERE contrato = ?", (contrato,)
    ).fetchone()
    if cliente is None:
        conn.close()
        return {"erro": "contrato_nao_encontrado", "contrato": contrato}
    bairro = conn.execute(
        "SELECT em_manutencao FROM bairros WHERE nome = ?", (cliente["bairro"],)
    ).fetchone()
    conn.close()
    if bairro and bairro["em_manutencao"]:
        return {"erro": "bairro_em_manutencao_nao_agendar_individual", "bairro": cliente["bairro"]}
    return {"proposta": True, "contrato": contrato, "data": data}


def agendar_visita_tecnico(contrato: str, data: str, confirmado_pelo_cliente: bool) -> dict:
    """Escrita irreversível de custo (desloca um técnico). Só executa se
    confirmado_pelo_cliente=True. No grafo (src/grafo.py) esse valor nunca vem
    do modelo: quem passa True é o nó de aprovação, depois que uma pessoa
    respondeu ao interrupt. Idempotente: repetir contrato e data devolve o
    registro existente com ja_existia=True, sem criar outra linha."""
    if not confirmado_pelo_cliente:
        return {"erro": "confirmacao_do_cliente_necessaria"}
    erro_data = validar_data(data, ate_dias=config.DIAS_MAXIMOS_VISITA)
    if erro_data:
        return erro_data
    conn = db.conectar()
    cliente = conn.execute(
        "SELECT bairro FROM clientes WHERE contrato = ?", (contrato,)
    ).fetchone()
    if cliente is None:
        conn.close()
        return {"erro": "contrato_nao_encontrado", "contrato": contrato}
    bairro = conn.execute(
        "SELECT em_manutencao FROM bairros WHERE nome = ?", (cliente["bairro"],)
    ).fetchone()
    if bairro and bairro["em_manutencao"]:
        conn.close()
        return {
            "erro": "bairro_em_manutencao_nao_agendar_individual",
            "bairro": cliente["bairro"],
        }
    chave = chave_visita(contrato, data)
    existente = conn.execute(
        "SELECT id FROM visitas WHERE chave = ?", (chave,)
    ).fetchone()
    if existente is not None:
        conn.close()
        return {"contrato": contrato, "data": data, "status": "AGENDADA", "ja_existia": True}
    conn.execute(
        "INSERT INTO visitas (contrato, data, status, chave) VALUES (?, ?, 'AGENDADA', ?)",
        (contrato, data, chave),
    )
    conn.commit()
    conn.close()
    return {"contrato": contrato, "data": data, "status": "AGENDADA", "ja_existia": False}


FERRAMENTAS_OPENAI = [
    {
        "type": "function",
        "function": {
            "name": "obter_data_atual",
            "description": "Retorna a data de hoje e a de amanhã. Chame antes de propor uma visita técnica — você não tem relógio.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "testar_linha",
            "description": "Roda o teste automático de sinal na linha do cliente. Leitura, não altera nada.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "conferir_queda_bairro",
            "description": "Descobre o bairro do cliente pelo contrato e verifica se está em manutenção geral.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reiniciar_conexao",
            "description": "Reinicia a conexão do cliente à distância. Só use se não houver falha física (sinal <= -27dBm).",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propor_visita",
            "description": (
                "Propõe uma visita técnica para hoje ou amanhã. Não agenda: o sistema "
                "pausa e pergunta ao cliente, que aprova, rejeita ou troca a data. "
                "Só use depois de testar_linha confirmar falha física. Chame "
                "obter_data_atual antes e use a data de amanhã."
            ),
            "parameters": {
                "type": "object",
                "properties": {"data": {"type": "string", "description": "AAAA-MM-DD"}},
                "required": ["data"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_base_conhecimento",
            "description": (
                "Consulta os manuais e políticas do provedor (sintomas, limiares, regras "
                "de atendimento). Leitura. Não responde sobre o estado atual da linha ou "
                "do bairro do cliente: para isso use testar_linha e conferir_queda_bairro. "
                "Se retornar suficiente=false, o manual não cobre a pergunta."
            ),
            "parameters": {
                "type": "object",
                "properties": {"pergunta": {"type": "string"}},
                "required": ["pergunta"],
            },
        },
    },
]

# O modelo NÃO tem agendar_visita_tecnico: só propor_visita. O agendamento é
# executado pelo nó `agendar` do grafo, depois da aprovação humana.
FUNCOES = {
    "obter_data_atual": obter_data_atual,
    "testar_linha": testar_linha,
    "conferir_queda_bairro": conferir_queda_bairro,
    "reiniciar_conexao": reiniciar_conexao,
    "propor_visita": propor_visita,
    "consultar_base_conhecimento": rag.consultar_base_conhecimento,
}

FUNCOES_INTERNAS = {"agendar_visita_tecnico": agendar_visita_tecnico}
