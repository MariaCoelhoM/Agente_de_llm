# Observabilidade (Parte 3, §4)

O plano vem primeiro, porque é ele que decide o que instrumentar. A instrumentação está em `src/observabilidade.py` e nos pontos que a chamam (`src/chat.py`, `src/grafo.py`).

## 1. O plano

### 1.1 As quatro perguntas

| Interessado | Pergunta | Decisão que a resposta muda | Sinal que responde |
|---|---|---|---|
| **o negócio** (gerente da operação) | Que fração dos atendimentos o agente resolve **sem** transbordo, e quantos terminam com uma resposta que precisou ser corrigida? | ampliar o agente para mais bairros, ou recuar e mandar mais casos direto para o atendente | `app.saida.encaminhar_humano`, `app.motivo_termino`, `app.saida.afirmacoes_bloqueadas` na raiz |
| **a operação** (quem mantém o sistema no ar) | O agente está terminando **bem** ou parando no meio? Qual ferramenta falha, e quanto? | abrir incidente, suspender o agente (C5) ou só observar | distribuição de `app.motivo_termino`; spans `execute_tool` com status `ERROR` e `error.type` |
| **quem paga** | Quanto custa um atendimento, e quanto custa o mês no volume do case (5.400)? | trocar de modelo, reduzir a janela de conversa, encurtar o prompt | `gen_ai.usage.input_tokens` / `output_tokens` e `app.custo_usd` na raiz |
| **quem responde pelo sistema** (responsável técnico) | Numa execução específica, **por que** o agente fez o que fez, e sob qual versão de código, prompt e modelo? | corrigir, reverter uma versão, responder a uma reclamação | o trace inteiro: `app.entrada`, os `execute_tool` com argumentos e resultado, `app.rag.trechos`, `app.versao_sistema`, `app.prompt.*.sha256`, `gen_ai.request.model`, `app.motivo_termino`, eventos `aprovacao_humana` |

### 1.2 O trace de uma execução

Uma **execução** é um turno da conversa (uma invocação do grafo). A conversa inteira é ligada por `gen_ai.conversation.id` (= `thread_id`). Árvore típica de um turno com visita (caso G07, `evals/resultados/3.0.0_regras/traces.jsonl`, trace `cacacd6b…`):

```
invoke_agent suporte_tecnico_domestico            raiz, 1 por turno (src/chat.py)
├── chat regras-v1                                 nó agente: decide testar_linha
├── execute_tool testar_linha                      {"status": "OFFLINE", "sinal_dbm": -30.0, "falha_fisica_provavel": true}
├── chat regras-v1                                 decide conferir_queda_bairro
├── execute_tool conferir_queda_bairro             {"bairro": "Vila Nova", "em_manutencao": false}
├── chat regras-v1                                 decide propor_visita
└── execute_tool propor_visita                     {"proposta": true, "data": "2026-11-13"}
    evento na raiz: aguardando_aprovacao           app.motivo_termino = aguardando_humano

invoke_agent suporte_tecnico_domestico            turno seguinte: a resposta "sim" do cliente
├── chat regras-v1                                 escreve a resposta final
    evento na raiz: aprovacao_humana               decisao=aprovar, quem, texto_cliente="sim", resultado AGENDADA
```

Spans nas convenções GenAI do OpenTelemetry:

| Span | Quando abre | Atributos da convenção |
|---|---|---|
| `invoke_agent suporte_tecnico_domestico` | um por turno, como raiz | `gen_ai.operation.name`, `gen_ai.agent.name`, `gen_ai.provider.name`, `gen_ai.request.model`, `gen_ai.conversation.id`, `gen_ai.usage.*` |
| `chat <modelo>` | cada chamada ao modelo (nó `agente`) | `gen_ai.request.model`, `gen_ai.request.temperature`, `gen_ai.request.max_tokens`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.response.finish_reasons`, `error.type` |
| `execute_tool <ferramenta>` | cada ferramenta executada (nó `ferramentas`) | `gen_ai.tool.name`, `gen_ai.tool.type`, `gen_ai.tool.call.id`, `gen_ai.tool.call.arguments`, `gen_ai.tool.call.result`, `error.type` |

Atributos próprios da raiz (prefixo `app.`):

| Atributo | Para quê |
|---|---|
| **`app.motivo_termino`** (obrigatório) | a taxonomia de 15 motivos (`src/guardas.py`), mais `aguardando_humano` |
| **`app.versao_sistema`** (obrigatório) | corte por versão; também em `service.version` do recurso |
| `app.entrada` | o texto do cliente, **com dado pessoal mascarado** (a tentativa de injeção fica, para auditoria) |
| `app.contrato`, `app.identidade.origem`, `app.identidade.contrato_digitado_ignorado` | quem, e se tentaram trocar o contrato (C1) |
| `app.prompt.sistema`, `app.prompt.sistema.sha256`, `app.prompt.procedural.sha256`, `app.commit`, `gen_ai.request.temperature` | as versões de prompt e código |
| `app.rag.trechos_recuperados` (e `app.rag.trechos` em cada consulta) | o contexto recuperado, por identificador |
| `app.saida.resultado`, `app.saida.suficiente`, `app.saida.encaminhar_humano`, `app.saida.fontes`, `app.saida.motivo_insuficiencia`, `app.saida.afirmacoes_bloqueadas` | a saída e a correção do C4 |
| `app.turno`, `app.turno.tipo`, `app.voltas`, `app.custo_usd` | posição na conversa e custo |
| eventos `aguardando_aprovacao` e `aprovacao_humana` | a pausa e a decisão humana: quem, quando (timestamp do evento), o que foi aprovado, o texto digitado, o resultado |

### 1.3 Os modos de falha

| # | Modo de falha | Silenciosa? | Sinal que o torna visível |
|---|---|---|---|
| F1 | o modelo **afirma o que não aconteceu** ("agendei", "resolvido") | **sim** — termina em `resposta_final`, sem erro | `app.saida.afirmacoes_bloqueadas` não vazio (C4); entra como execução **ruim** no SLI |
| F2 | **recusa demais**: o portão do RAG ou a falta de fonte faz o agente responder `suficiente=false` para perguntas que o manual cobre (ex.: o corpus mudou e o índice não) | **sim** — termina em `resposta_final` | proporção de `app.saida.motivo_insuficiencia = fora_do_corpus` / `sem_fonte` por versão; `app.rag.trechos` vazio |
| F3 | **o modelo do provedor muda** (preview na Groq, risco R1) e o agente passa a usar mais voltas ou outras ferramentas | **sim** | `app.voltas` e tokens médios por versão sobem sem mudança de código; delta na suíte (`evals.comparar`) |
| F4 | **orçamento esgotado**: o turno para por voltas, tokens, tempo ou laço, e o cliente vai para humano com resposta genérica | parcialmente — não é erro, é término | `app.motivo_termino` em `limite_de_voltas`, `tokens_esgotados`, `tempo_esgotado`, `laco_detectado`, `conversa_longa` |
| F5 | **ferramenta indisponível** (banco travado) | não | span `execute_tool` com status `ERROR`, `error.type = ferramenta_indisponivel`; `app.motivo_termino = ferramenta_indisponivel` |
| F6 | **provedor fora, chave inválida ou host recusado** (C2) | não | span `chat` com `ERROR`, `error.type`; `app.motivo_termino = erro_fatal_llm` |

### 1.4 O objetivo

Detalhado no §4.

## 2. A instrumentação

- **Onde:** `src/observabilidade.py` (configuração, exportador, spans), `src/chat.py` (raiz por turno e atributos de entrada/saída/custo), `src/grafo.py` (spans `chat` e `execute_tool`, evento `aprovacao_humana`).
- **Pai explícito:** os nós do LangGraph podem rodar em outra thread; o span pai é procurado pelo `thread_id` da conversa, não pelo contexto implícito. O teste `tests/test_chat.py::test_trace_tem_raiz_com_motivo_e_versao` confere que todos os spans de um turno têm o mesmo `trace_id` da raiz.
- **Destino consultável:** arquivo JSONL, um span por linha, em `logs/traces/AAAA-MM-DD.jsonl` (uso do chat) ou em `evals/resultados/<rodada>/traces.jsonl` (suíte). Se `OTEL_EXPORTER_OTLP_ENDPOINT` estiver no `.env`, os spans também vão por OTLP/HTTP para um coletor com interface (Jaeger, Arize Phoenix, Grafana Tempo).
- **Como ver:** `python -m scripts.ver_traces` (árvore no terminal) — ver README, "Como ver os traces".

## 3. As métricas, sobre execuções reais

Fonte: os traces das duas rodadas commitadas da suíte, **41 execuções (turnos) em 30 conversas por versão**, com corte por `app.versao_sistema`. Comando:

```bash
python -m evals.metricas evals/resultados/2.1.0_regras evals/resultados/3.0.0_regras
```

(saída completa em `evals/resultados/metricas_2.1.0_x_3.0.0.json`)

| Métrica | 2.1.0 (anterior) | 3.0.0 (nova) |
|---|---|---|
| execuções / conversas | 41 / 30 | 41 / 30 |
| latência p50 / p95 | 25,6 ms / 39,9 ms | 27,7 ms / 38,7 ms |
| tokens médios por execução (entrada / saída) | 1.931 / 53 | 1.996 / 55 |
| custo por execução (US$ 0,80 / 4,00 por 1M) | US$ 0,00176 | US$ 0,00182 |
| motivos de término | resposta_final 27 · aguardando_humano 9 · entrada_incompleta 2 · aprovacao_expirada 1 · encaminhado_humano 1 · laco_detectado 1 | resposta_final 26 · aguardando_humano 9 · aprovacao_expirada 2 · entrada_incompleta 2 · encaminhado_humano 1 · laco_detectado 1 |
| erro por ferramenta | conferir_queda_bairro 1/20 · reiniciar_conexao 1/8 · testar_linha 1/26 · propor_visita 0/9 · consultar_base 0/3 | conferir_queda_bairro 1/21 · reiniciar_conexao 1/9 · testar_linha 1/28 · propor_visita 0/9 · consultar_base 0/3 |
| respostas corrigidas pelo C4 | 0 | 2 |

**Como ler estes números — e o que eles não dizem.** As rodadas usam o **modelo de regras** (`docs/evals.md` §5), não o LLM:

- **latência:** é a do código em volta do modelo (grafo, SQLite, trace); **não inclui a chamada ao provedor**. Com o modelo real, a latência é dominada pela Groq. **LACUNA**: falta a rodada com `--modelo real`.
- **tokens de entrada** são uma boa aproximação do real: o modelo de regras conta os caracteres das mensagens que o sistema de fato montou (prompt, memória, histórico, retornos de ferramenta) ÷ 4. Os de **saída** são fictícios (20 por chamada de ferramenta + texto). Por isso o custo acima é uma estimativa por baixo; os logs reais da Parte 2 dão ~US$ 0,005 por execução (`docs/modelos.md` §2.1).
- **erros de ferramenta** são esperados na suíte: `testar_linha` 1 = contrato C999 (G20); `conferir_queda_bairro` 1 = bairro sem cadastro (G21); `reiniciar_conexao` 1 = a 3ª chamada bloqueada pelo detector de laço (G26). Nenhum é defeito; numa operação real, os três seriam lidos de outro jeito (o C999 é cadastro, os outros dois são alarme).

### Respostas às quatro perguntas, com os números

1. **Negócio — quanto se resolve sem transbordo?** Na 3.0.0, 6 dos 28 casos terminaram com `encaminhar_humano=true` (G11 aprovação expirada, G15 e G18 fora do corpus, G16 cobrança, G26 laço, G27 — a 2ª conversa — aprovação expirada): **22/28 = 79% sem transbordo**, e **2 respostas precisaram de correção** (G25 e a 1ª conversa do G27). Na 2.1.0 o mesmo número parecia melhor porque as duas respostas falsas saíam sem correção — **é exatamente a degradação silenciosa F1**. *Ressalva:* a suíte é adversarial (5 casos de segurança em 28); não é a mistura do dia a dia. A pergunta só fica respondida de verdade com tráfego real.
2. **Operação — termina bem? qual ferramenta falha?** 26 `resposta_final` + 9 pausas em 41; 1 laço; nenhuma `ferramenta_indisponivel`, nenhum `erro_fatal_llm`, nenhum estouro de orçamento. As três falhas de ferramenta são as esperadas (acima). Decisão: nenhuma ação.
3. **Quem paga — quanto custa?** ~US$ 0,0018 por turno pelo volume de entrada medido (por baixo); com os logs reais da Parte 2, ~US$ 0,005 → ~US$ 27/mês em 5.400 atendimentos. **LACUNA:** custo medido com o modelo real.
4. **Quem responde — por que o agente fez aquilo?** Respondida: a reconstrução de uma decisão só a partir do trace está em `docs/model-card.md` §11.

## 4. O objetivo: SLI e SLO de qualidade

**SLI — fração das execuções válidas que terminam bem.** Definição exata (`evals/metricas.py`):

- **evento = uma raiz** `invoke_agent` (um turno);
- **válidas** = todas, menos `app.motivo_termino = agente_suspenso` (suspensão é decisão da operação, não falha do agente);
- **boas** = válidas com `app.motivo_termino ∈ {resposta_final, aguardando_humano, entrada_incompleta, encaminhado_humano}` **e** `app.saida.afirmacoes_bloqueadas` ausente;
- **ruins**, por consequência: orçamento esgotado (`limite_de_voltas`, `limite_de_ferramentas`, `tokens_esgotados`, `tempo_esgotado`, `conversa_longa`), `laco_detectado`, `recursion_limit`, `erro_fatal_llm`, `ferramenta_indisponivel`, `aprovacao_expirada`, e qualquer `resposta_final` que o verificador C4 precisou corrigir.

O SLI cobre a **degradação silenciosa**: execução que termina sem erro mas por orçamento esgotado, ou com resposta corrigida, não move nenhuma taxa de erro — só este objetivo a vê.

**SLO: ≥ 95% de execuções boas, em janela de 7 dias.** Orçamento de erro: 5% das execuções da janela.

**Valor medido** (41 execuções por versão, rodadas da suíte):

| Versão | Boas / válidas | SLI | SLO 95% | Orçamento de erro consumido |
|---|---|---|---|---|
| 2.1.0 | 39 / 41 | 95,1% | cumprido | 98% |
| 3.0.0 | 36 / 41 | **87,8%** | **violado** | **244%** |

**Leitura honesta.** A 3.0.0 viola o SLO **e é melhor que a 2.1.0**. A 2.1.0 "cumpre" porque as duas respostas falsas (G25, G27) saíam como `resposta_final` comum — o sinal não existia. A 3.0.0 as detecta e corrige (2 ruins), e a 2ª conversa do G27, sem a instrução envenenada na memória, segue o diagnóstico normal, chega à aprovação e expira (o caso não traz resposta do cliente), em vez de afirmar o falso (mais 1 ruim). As 5 ruins da 3.0.0: 2 corrigidas pelo C4, 2 aprovações expiradas (G11 e G27), 1 laço (G26) — **todas provocadas de propósito** pelos casos adversariais da suíte.

**O que faríamos:** não baixar o objetivo para caber no número (isso não é objetivo). (1) Medir o SLO sobre **tráfego** (o chat com o modelo real), não sobre a suíte adversarial, que existe para provocar exatamente os términos ruins; (2) separar no SLI as aprovações expiradas por ausência do cliente (não é falha do agente, mas é cliente sem resolução — fica como ruim até termos dado para decidir); (3) se o SLO continuar violado no tráfego real, a primeira alavanca é o F1: quantas correções do C4 vêm de injeção e quantas de alucinação do modelo.
