import os

from dotenv import load_dotenv

load_dotenv()

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PASTA_DADOS = os.path.join(RAIZ, "dados")
PASTA_CORPUS = os.path.join(PASTA_DADOS, "corpus")
PASTA_PROMPTS = os.path.join(os.path.dirname(__file__), "prompts")
PASTA_LOGS = os.path.join(RAIZ, "logs")

CAMINHO_CHECKPOINTS = os.path.join(PASTA_DADOS, "checkpoints.db")
CAMINHO_MEMORIA = os.path.join(PASTA_DADOS, "memoria.db")

MODELO = os.environ.get("LLM_MODEL", "qwen/qwen3.8-27b")
TEMPERATURE = 0.2
MAX_TOKENS_RESPOSTA = 500

PROMPT_SISTEMA = "suporte_v2.md"
PROMPT_PROCEDURAL = "procedural.md"

# Orçamento do laço: passos e tempo.
MAX_VOLTAS_AGENTE = 6          # chamadas ao modelo por atendimento (antes: MAX_MENSAGENS)
MAX_PASSOS_FERRAMENTA = 8      # chamadas de ferramenta por atendimento
MAX_TESTES_LINHA = 3           # regra do domínio (case §2.2)
TETO_TOKENS = 12000            # tokens acumulados (entrada + saída) por atendimento
TENTATIVAS_LLM = 3             # tentativas em erro recuperável (limite de taxa, rede, timeout)
TETO_SEGUNDOS = 120            # tempo de parede do atendimento, sem contar a espera humana
REPETICOES_PARA_LACO = 3       # mesma ferramenta com os mesmos argumentos N vezes = laço     

RECURSION_LIMIT = 25

PRAZO_APROVACAO_SEGUNDOS = 15 * 60
DIAS_MAXIMOS_VISITA = 14

RAG_K = 3
RAG_COBERTURA_MINIMA = 0.5

DECAIMENTO_DIAS = 180
MEMORIA_EPISODIOS_MAX = 3
ORCAMENTO_TOKENS = {
    "system_prompt": 400,
    "ultimo_resultado": 150,
    "trajetoria": 1200,
    "memoria_longo_prazo": 500,
    "trechos_rag": 800,
}
