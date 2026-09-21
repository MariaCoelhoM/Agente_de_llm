"""
Laço principal do agente de suporte técnico doméstico.
Requisitos cobertos (item 4.1): laço com estado explícito, orçamento,
terminação registrada, log de trajetória, erro de ferramenta como dado.
"""
import os
import json
import datetime
from dotenv import load_dotenv
from openai import OpenAI

from . import tools

load_dotenv()  # lê o .env automaticamente — funciona igual em qualquer
                # sistema operacional, sem precisar exportar variável manual
MODELO = os.environ.get("LLM_MODEL", "qwen/qwen3.8-27b")

# Técnica: zero-shot com contrato de saída explícito no papel do agente.
# Por quê: a tarefa é curta (triagem + 1-2 ferramentas) e o contrato de
# saída (nunca falar de cobrança, nunca agendar sem "sim" do cliente) é
# o que impede a ação irreversível sem autorização — não precisa de
# exemplos few-shot para isso. Ver prompts/suporte_v1.md.
# Técnica: zero-shot com contrato de saída explícito no papel do agente.
# Por quê: a tarefa é curta (triagem + 1-2 ferramentas) e o contrato de
# saída (nunca falar de cobrança, nunca agendar sem "sim" do cliente) é
# o que impede a ação irreversível sem autorização — não precisa de
# exemplos few-shot para isso. Ver prompts/suporte_v1.md.
SYSTEM_PROMPT = """\
Você é o assistente de suporte técnico doméstico de um provedor de internet.

O que você faz: testa a linha do cliente, verifica queda geral no bairro e
reinicia a conexão à distância. Se detectar falha física (sinal <= -27dBm),
explique o motivo, chame obter_data_atual para saber que dia é hoje, e
proponha diretamente a visita para o dia seguinte (regra do domínio: no
máximo o dia seguinte) — peça só a confirmação do cliente ("sim"/"não"),
NÃO pergunte que data ele prefere. Se o bairro estiver em manutenção, NUNCA
ofereça ou proponha agendar visita técnica individual — explique que a
equipe de rede já está atuando na região e que o serviço volta quando a
manutenção terminar.

Contrato de saída — proibido:
- Nunca responda sobre cobrança, fatura ou desconto. Diga que isso não é
  suporte técnico e que vai encaminhar para um atendente humano.
- Nunca chame agendar_visita_tecnico com confirmado_pelo_cliente=true sem
  que o cliente tenha respondido "sim" na conversa.
- Nunca diga que o problema foi resolvido sem rodar testar_linha de novo
  depois de reiniciar_conexao para confirmar.
- Nunca pergunte ao cliente qual data ele prefere para a visita — chame
  obter_data_atual e proponha o dia seguinte, só peça a confirmação dele.

Isso impede: cobrar o cliente sem autorização, mandar técnico sem
consentimento, fechar o atendimento com a internet ainda fora do ar, e
empurrar para o cliente uma decisão (qual data agendar) que é do sistema.
"""

MAX_TESTES_LINHA = 3
MAX_MENSAGENS = 6
MAX_PASSOS_FERRAMENTA = 8  # orçamento geral de chamadas de ferramenta


class EstadoAtendimento:
    """Memória explícita do laço (não é só a lista de mensagens)."""

    def __init__(self, contrato_esperado: str):
        self.contrato_esperado = contrato_esperado
        self.testes_de_linha = 0
        self.tentou_reiniciar = False


def chamar_ferramenta(nome: str, args: dict, estado: EstadoAtendimento) -> dict:
    if nome == "testar_linha":
        if estado.testes_de_linha >= MAX_TESTES_LINHA:
            return {"erro": "limite_de_testes_atingido", "maximo": MAX_TESTES_LINHA}
        estado.testes_de_linha += 1
    if nome == "reiniciar_conexao":
        estado.tentou_reiniciar = True

    funcao = tools.FUNCOES.get(nome)
    if funcao is None:
        return {"erro": "ferramenta_desconhecida", "nome": nome}
    return funcao(**args)


def rodar_atendimento(client: OpenAI, mensagem_inicial: str, contrato: str, log_path: str):
    estado = EstadoAtendimento(contrato_esperado=contrato)
    mensagens = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"[contrato: {contrato}] {mensagem_inicial}"},
    ]
    trajetoria = []
    passos_ferramenta = 0
    motivo_parada = None

    trocas = 0
    while True:
        trocas += 1
        if trocas > MAX_MENSAGENS:
            motivo_parada = "limite_de_mensagens_atingido"
            break

        resposta = client.chat.completions.create(
            model=MODELO,
            messages=mensagens,
            tools=tools.FERRAMENTAS_OPENAI,
            max_tokens=500,
        )
        msg = resposta.choices[0].message
        mensagens.append(msg.model_dump(exclude_none=True))

        if not msg.tool_calls:
            trajetoria.append({"tipo": "resposta_final", "conteudo": msg.content})
            motivo_parada = "resposta_final_do_modelo"
            break

        parar = False
        for chamada in msg.tool_calls:
            if passos_ferramenta >= MAX_PASSOS_FERRAMENTA:
                motivo_parada = "orcamento_de_ferramentas_esgotado"
                parar = True
                break
            passos_ferramenta += 1
            args = json.loads(chamada.function.arguments or "{}")
            resultado = chamar_ferramenta(chamada.function.name, args, estado)
            trajetoria.append(
                {
                    "tipo": "ferramenta",
                    "nome": chamada.function.name,
                    "args": args,
                    "resultado": resultado,
                }
            )
            mensagens.append(
                {
                    "role": "tool",
                    "tool_call_id": chamada.id,
                    "content": json.dumps(resultado, ensure_ascii=False),
                }
            )
        if parar:
            break

    ultima = mensagens[-1]
    registro = {
        "timestamp": datetime.datetime.now().isoformat(),
        "modelo": MODELO,
        "contrato": contrato,
        "mensagem_inicial": mensagem_inicial,
        "trajetoria": trajetoria,
        "motivo_parada": motivo_parada,
        "resposta_final": ultima.get("content") if ultima.get("role") == "assistant" else None,
    }
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(registro, f, ensure_ascii=False, indent=2)

    return registro


if __name__ == "__main__":
    import sys
    from . import db

    db.inicializar()
    client = OpenAI(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["OPENAI_API_KEY"],
    )
    contrato = sys.argv[1] if len(sys.argv) > 1 else "C001"
    mensagem = sys.argv[2] if len(sys.argv) > 2 else "Minha internet caiu."
    log_path = f"logs/caso_{contrato}.json"
    registro = rodar_atendimento(client, mensagem, contrato, log_path)
    print(f"Parou por: {registro['motivo_parada']}")
    print(f"Log salvo em: {log_path}")