"""
Ferramentas do agente. Cada função retorna um dict (nunca lança exceção para
fora): erro de ferramenta é dado que o modelo lê e usa para se corrigir
(requisito 4.1 — "erro de ferramenta como dado").
"""
import datetime
from . import db


def obter_data_atual() -> dict:
    """Leitura, sem argumentos. O modelo não tem relógio; chama isso sempre
    que precisar saber a data de hoje, por exemplo antes de propor uma
    visita técnica para o dia seguinte (regra do domínio, case §2.1)."""
    hoje = datetime.date.today()
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


def agendar_visita_tecnico(contrato: str, data: str, confirmado_pelo_cliente: bool) -> dict:
    """Escrita irreversível de custo (desloca um técnico). Só executa se
    confirmado_pelo_cliente=True — o modelo só pode passar True depois de o
    cliente ter respondido "sim" na conversa (contrato de saída no prompt)."""
    if not confirmado_pelo_cliente:
        return {"erro": "confirmacao_do_cliente_necessaria"}
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
    conn.execute(
        "INSERT INTO visitas (contrato, data, status) VALUES (?, ?, 'AGENDADA')",
        (contrato, data),
    )
    conn.commit()
    conn.close()
    return {"contrato": contrato, "data": data, "status": "AGENDADA"}


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
                "properties": {"contrato": {"type": "string"}},
                "required": ["contrato"],
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
                "properties": {"contrato": {"type": "string"}},
                "required": ["contrato"],
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
                "properties": {"contrato": {"type": "string"}},
                "required": ["contrato"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "agendar_visita_tecnico",
            "description": "Agenda visita técnica. SÓ chame com confirmado_pelo_cliente=true depois que o cliente disser explicitamente sim.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contrato": {"type": "string"},
                    "data": {"type": "string", "description": "Data no formato AAAA-MM-DD"},
                    "confirmado_pelo_cliente": {"type": "boolean"},
                },
                "required": ["contrato", "data", "confirmado_pelo_cliente"],
            },
        },
    },
]

FUNCOES = {
    "obter_data_atual": obter_data_atual,
    "testar_linha": testar_linha,
    "conferir_queda_bairro": conferir_queda_bairro,
    "reiniciar_conexao": reiniciar_conexao,
    "agendar_visita_tecnico": agendar_visita_tecnico,
}