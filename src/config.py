import os

from dotenv import load_dotenv

load_dotenv()

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PASTA_DADOS = os.path.join(RAIZ, "dados")
PASTA_CORPUS = os.path.join(PASTA_DADOS, "corpus")
PASTA_PROMPTS = os.path.join(os.path.dirname(__file__), "prompts")
PASTA_LOGS = os.path.join(RAIZ, "logs", "execucoes")   # logs de execução locais (fora do git)
PASTA_TRACES = os.path.join(RAIZ, "logs", "traces")     # traces OpenTelemetry locais (fora do git)
ARQUIVO_SUSPENSAO = os.path.join(RAIZ, "dados", "SUSPENSO")  # kill switch (§2.2 da Parte 3)

# Versão do sistema: carimbada na raiz de cada trace e em cada rodada da suíte.
# Mudou o comportamento (código, prompt, modelo, parâmetro)? Suba a versão.
VERSAO_SISTEMA = "3.0.0"

CAMINHO_CHECKPOINTS = os.path.join(PASTA_DADOS, "checkpoints.db")
CAMINHO_MEMORIA = os.path.join(PASTA_DADOS, "memoria.db")

# Modelo e parâmetros: carimbados no log de cada execução.
MODELO = os.environ.get("LLM_MODEL") or "qwen/qwen3.8-27b"
TEMPERATURE = 0.2
MAX_TOKENS_RESPOSTA = 500

PROMPT_SISTEMA = "suporte_v3.md"
PROMPT_PROCEDURAL = "procedural.md"

# Orçamento do laço: passos e tempo.
MAX_VOLTAS_AGENTE = 6          # chamadas ao modelo por TURNO da conversa
MAX_PASSOS_FERRAMENTA = 8      # chamadas de ferramenta por turno
MAX_TESTES_LINHA = 3           # regra do domínio
TETO_TOKENS = 12000            # tokens acumulados (entrada + saída) por turno
TENTATIVAS_LLM = 3             # tentativas em erro recuperável (limite de taxa, rede, timeout)
TETO_SEGUNDOS = 120            # tempo de máquina do turno, sem contar a espera humana
REPETICOES_PARA_LACO = 3       # mesma ferramenta com os mesmos argumentos N vezes = laço

# Limite de passos do LangGraph por invocação (um turno). O turno mais
# longo legítimo gasta cerca de 19 passos. O estouro é um motivo de término
# nosso (recursion_limit), não uma exceção que derruba.
RECURSION_LIMIT = 25

# A conversa (chat). Um atendimento = uma conversa = um thread_id.
MAX_TURNOS_CONVERSA = 12       # mensagens do cliente por conversa; depois disso, transbordo
TETO_TOKENS_CONVERSA = 60000   # tokens somados de todos os turnos
JANELA_TURNOS = 4              # quantos turnos do cliente (com as respostas) vão ao modelo
TENTATIVAS_RESPOSTA_APROVACAO = 3  # respostas que o código não entende antes de tratar como "rejeitar"

# Aprovação humana
PRAZO_APROVACAO_SEGUNDOS = 15 * 60
DIAS_MAXIMOS_VISITA = 14

# RAG: corte por estrutura do documento, k e portão escolhidos
# a partir da medição.
RAG_K = 3
RAG_COBERTURA_MINIMA = 0.5

# Memória.
DECAIMENTO_DIAS = 180
MEMORIA_EPISODIOS_MAX = 3
ORCAMENTO_TOKENS = {
    "system_prompt": 400,
    "ultimo_resultado": 150,
    "trajetoria": 1200,
    "memoria_longo_prazo": 500,
    "trechos_rag": 800,
}

# Custo (US$ por 1 milhão de tokens) do modelo em uso, para a métrica de custo
# por execução. Valores da Groq para qwen/qwen3.8-27b (preview), consultados em
# 12/11/2026 (docs/fontes.md). Sobrescreva no .env se trocar de modelo.
PRECO_ENTRADA_MTOK = float(os.environ.get("PRECO_ENTRADA_MTOK") or "0.80")  # vazio no .env = padrão
PRECO_SAIDA_MTOK = float(os.environ.get("PRECO_SAIDA_MTOK") or "4.00")

# Provedores aos quais a chave de API pode ser enviada (controle C2, docs/seguranca.md).
# Um LLM_BASE_URL fora desta lista é recusado ANTES de qualquer requisição.
HOSTS_LLM_PERMITIDOS = {
    "api.groq.com", "api.mistral.ai", "api.openai.com", "localhost", "127.0.0.1",
}

# Controles da Parte 3 (docs/seguranca.md §2). Ligados por padrão. Não são lidos
# do ambiente de propósito: só a suíte de avaliação os desliga, em processo,
# para medir a versão anterior (evals/rodar.py --versao-anterior).
CONTROLES = {
    "identidade_pelo_canal": True,     # C1 — ASI03
    "memoria_sanitizada": True,        # C3 — ASI06
    "verificador_de_afirmacoes": True,  # C4 — ASI09/ASI01
}
