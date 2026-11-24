# Fontes consultadas

## Parte 1

- Preço Mistral Small: https://docs.mistral.ai/platform/pricing/ (consultado set/2026)
- Preço GPT-4o mini: https://developers.openai.com/api/docs/pricing (consultado set/2026)
- Preço Llama 3.1 8B Instant (Groq): https://groq.com/pricing (consultado set/2026)
- Case original: `exercicios/Agente de Suporte Técnico Doméstico.md` e
  `exercicios/Agente de Suporte Técnico Doméstico - parte 2.md` (material do grupo; transcritos dos PDFs originais, que saíram do repositório)

## Parte 2

- Enunciado da Segunda Entrega (material da disciplina), que define os itens 0 a 10 e os critérios de cada documento.
- Limite de gasto da conta Groq: https://console.groq.com/docs/spend-limits (citado em `docs/modelos.md` §5)
- LangGraph 1.2.16, código-fonte da biblioteca instalada: `langgraph/_internal/_config.py` linha 32, onde o padrão de `recursion_limit` é 10007 (consultado out/2026; ver `docs/grafo.md` §4).
- Versões fixadas das dependências: `requirements.txt`.

## Parte 3

- Preço do `qwen/qwen3.8-27b` na Groq (US$ 0,80 entrada / US$ 4,00 saída por 1M tokens, modelo em preview), consultado em 12/11/2026: https://computeprices.com/providers/groq/models/qwen3-8-27b e https://www.morphllm.com/groq-pricing
- OpenTelemetry — convenções semânticas para GenAI (spans `invoke_agent`, `chat`, `execute_tool`; atributos `gen_ai.*`): https://opentelemetry.io/docs/specs/semconv/gen-ai/
- OpenTelemetry Python SDK 1.38: https://opentelemetry-python.readthedocs.io/
- OWASP — Agentic AI Top 10 (ASI01–ASI10): https://genai.owasp.org/
- LGPD, Lei 13.709/2018, art. 7º (bases legais): https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm
- Google SRE Book, capítulo "Service Level Objectives" (SLI, SLO, orçamento de erro): https://sre.google/sre-book/service-level-objectives/
- Política de dados da Groq: https://console.groq.com/docs/your-data (consultado out/2026, exercício da Aula 12)
