# Análise de modelos

## 1. Os candidatos

Eixos escolhidos **para este caso**: tool calling é pré-requisito (sem ele
não há chamada de ferramenta); latência importa porque o cliente está
esperando resposta no WhatsApp; custo importa porque o volume é alto
(5.400 chamados/mês, §2.5 do case); janela de contexto e multimídia
importam pouco aqui — a conversa é curta e não há imagem nesta entrega
(fica para o agente do técnico, Parte 3).

| Eixo                                   | Mistral Small (`mistral-small-latest`) | GPT-4o mini | Llama 3.1 8B Instant (Groq) |
|----------------------------------------|----------------------------------------|-------------|-----------------------------|
| Janela de contexto                     | 32K                                           | 128K | 128K |
| Tool calling / saída estruturada       | sim                                           | sim | sim |
| Multimídia                             | não (texto)                                   | sim (imagem) | não |
| Raciocínio                             | suficiente para classificação + decisão curta | mais forte, útil se o prompt crescer | mais fraco em instrução composta |
| Custo (entrada / saída, por 1M tokens) | US$ 0,20 / US$ 0,60                           | US$ 0,15 / US$ 0,60 | US$ 0,05 / US$ 0,08 |
| Latência                               | baixa                                                  | baixa | muito baixa (hardware LPU da Groq) |
| Onde roda                              | API pública Mistral                                       | API pública OpenAI | API pública Groq |
| Política de dados                      | dado do cliente trafega para a Mistral; não há residência de dados no Brasil | trafega para a OpenAI, mesma ressalva | trafega para a Groq, mesma ressalva |

**O modelo escolhido, nos mesmos eixos** (devolutiva da Parte 1: a análise
precisa cobrir o modelo em uso, que não era nenhum dos três acima):

| Eixo | Qwen3.8 27B (`qwen/qwen3.8-27b`, Groq) |
|---|---|
| Janela de contexto | suficiente para o caso (o maior turno medido na Parte 2 usou ~6.500 tokens somando todas as chamadas) |
| Tool calling / saída estruturada | sim — rodou os 10 casos da Parte 2 com tool calling (`logs/parte2/`) |
| Multimídia | não |
| Raciocínio | suficiente: seguiu a regra do bairro em manutenção e a de propor visita na falha física |
| Custo (entrada / saída, por 1M tokens) | **US$ 0,80 / US$ 4,00** (consultado em 12/11/2026, `docs/fontes.md`) — o mais caro dos quatro na saída |
| Latência | baixa (Groq) — sem medição própria com o modelo real nesta entrega: ver LACUNA em `docs/observabilidade.md` |
| Onde roda | API pública Groq; **modelo em preview** ("evaluation only") — pode ser retirado sem aviso |
| Política de dados | trafega para a Groq; mesma ressalva dos outros |

Preços consultados em setembro de 2026 nas páginas oficiais de cada
provedor (ver `docs/fontes.md`) — conferir antes de rodar em produção, pois
mudam com frequência.

## 2. A conta

Estimativa por execução (uma conversa completa: classificação + até 3
chamadas de ferramenta + resposta final ≈ 4 a 5 chamadas ao modelo):

tokens de entrada por chamada ≈ 600 (system prompt + histórico + resultado de ferramenta) tokens de saída por chamada ≈ 150 (texto curto ou tool call) nº de chamadas por execução ≈ 5

Mistral Small: entrada: 600 × 5 = 3.000 tokens × US$0,20/1M = US$0,0006 saída: 150 × 5 = 750 tokens × US$0,60/1M = US$0,00045 custo por execução ≈ US$ 0,001

GPT-4o mini: entrada: 3.000 × US$0,15/1M = US$0,00045 saída: 750 × US$0,60/1M = US$0,00045 custo por execução ≈ US$ 0,0009

Llama 3.1 8B (Groq): entrada: 3.000 × US$0,05/1M = US$0,00015 saída: 750 × US$0,08/1M = US$0,00006 custo por execução ≈ US$ 0,0002

Por 100 execuções: Mistral Small ≈ US$ 0,10; GPT-4o mini ≈ US$ 0,09; Llama
3.1 8B ≈ US$ 0,02.

Pelo volume do case (5.400 chamados/mês, §2.5): Mistral Small ≈ US$ 5,40/mês;
GPT-4o mini ≈ US$ 4,90/mês; Llama 3.1 8B ≈ US$ 1,10/mês. Nos três casos o
custo de rodar é irrelevante perto do ganho operacional estimado — a decisão
não deve ser guiada só por preço.

### 2.1 A conta do modelo escolhido, com tokens medidos

Os 9 logs da Parte 2 que chamaram o modelo (`logs/parte2/*.json`, campo
`tokens`) somam, por execução: 6005, 4513, 6498, 5924, 6472, 2850, 2781,
3183 e 3010 tokens — **média de 4.582 tokens por execução** (entrada + saída;
os logs da Parte 2 não separavam os dois). Supondo 90% de entrada e 10% de
saída (o prompt de sistema e o histórico dominam; a saída é curta):

```
entrada: 4.124 tokens × US$ 0,80/1M = US$ 0,0033
saída:     458 tokens × US$ 4,00/1M = US$ 0,0018
custo por execução                  ≈ US$ 0,0051
```

- por 100 execuções: ≈ **US$ 0,51**
- por mês, no volume do case (5.400 chamados): ≈ **US$ 27,50**
- **no semestre do grupo** (desenvolvimento e testes): ~10 rodadas da suíte
  de avaliação × 41 execuções + ~300 execuções manuais ≈ 710 execuções ≈
  **US$ 3,60** — coberto pelo nível gratuito da Groq, que limita requisições
  por minuto, não dinheiro.

Desde a Parte 3 o trace separa tokens de entrada e de saída
(`gen_ai.usage.input_tokens` / `output_tokens`) e calcula `app.custo_usd` por
execução; `python -m evals.metricas` reporta o custo medido por versão.

## 3. A verificação mínima

O comparativo do §1 é teórico (documentação e preço publicados pelos três
provedores). Testar de verdade os três exigiria uma chave paga da OpenAI e
ativar o Pay-as-you-go da Mistral (§4) — fora do escopo de uma entrega que
deve rodar sem custo. Por isso, a verificação empírica abaixo cobre só o
modelo realmente usado, `qwen/qwen3.8-27b` via Groq, contra 4 dos 5 casos
do `docs/case.md` §2.8:

| Caso | Ação esperada | Ação tomada pelo agente | Resultado |
|---|---|---|---|
| C001 (simples) | reiniciar e confirmar que voltou | **Parte 1:** o log da Parte 1 termina com o agente perguntando "Posso tentar reiniciar a conexão à distância?", sem chamar `reiniciar_conexao` — a versão anterior desta tabela afirmava o contrário, e estava errada (devolutiva da Parte 1). **Parte 2:** `logs/parte2/caso_C001_feliz.json` mostra `testar_linha → conferir_queda_bairro → reiniciar_conexao → testar_linha` e a resposta ONLINE | ✅ correto na Parte 2 (com evidência no log) |
| C002 (divergência) | não fechar como "resolvido" sem investigar; achar a causa real | descobriu o bairro pelo contrato, viu que estava em manutenção, explicou a causa real e recusou agendar visita individual | ✅ correto |
| C999 (inexistente) | tratar o erro como dado, sem quebrar, pedir o contrato certo | recebeu `contrato_nao_encontrado` e pediu o número certo ao cliente | ✅ correto |
| C005 (bairro em manutenção) | não agendar visita individual | na primeira tentativa ofereceu agendar mesmo assim (inconsistente com C002); depois de ajustar o `SYSTEM_PROMPT` para proibir isso explicitamente, passou a recusar do mesmo jeito que o C002 | ✅ correto, depois do ajuste — ver §4 |
| C004 (falha física) | não insistir em reiniciar; propor a data do dia seguinte e só agendar com "sim" do cliente | reconheceu o sinal de −30dBm como falha física, não chamou `reiniciar_conexao`, confirmou que o bairro não está em manutenção, chamou `obter_data_atual` e propôs a data certa (amanhã) pedindo só a confirmação | ✅ correto |

Os 5 casos do domínio (`docs/case.md` §2.8) estão validados para o modelo
escolhido.

**LACUNA (devolutiva da Parte 1, item 5c): os três candidatos não foram
rodados.** O instrumento para fazer isso agora existe: a suíte de avaliação
roda o golden dataset contra qualquer modelo compatível trocando duas
variáveis de ambiente.

```bash
# um modelo por vez, no .env: LLM_BASE_URL, OPENAI_API_KEY, LLM_MODEL
python -m evals.rodar --versao 3.0.0 --modelo real --nome 3.0.0_qwen3.8-27b
python -m evals.rodar --versao 3.0.0 --modelo real --nome 3.0.0_mistral-small
python -m evals.comparar evals/resultados/3.0.0_qwen3.8-27b evals/resultados/3.0.0_mistral-small
```

Enquanto essas rodadas não forem commitadas, a escolha continua sendo por
restrição prática (custo zero sem cartão, §4), e não por qualidade medida.

## 4. A decisão

Escolhido: **Qwen3 27B (`qwen/qwen3.8-27b`), via Groq**. Chegamos até aqui
depois de três trocas, e vale registrar por quê, porque isso também é parte
da análise:

1. A avaliação inicial havia apontado o Mistral Small, mas na prática a
   chave gratuita da Mistral fica travada em um limite de taxa muito baixo
   até a conta ativar o bloco "API Pay-as-you-go" — que exige confirmação
   de telefone e é apresentado como parte da assinatura paga, não do tier
   gratuito puro.
2. Trocamos para a Groq com `llama-3.1-8b-instant`, que tinha o custo mais
   baixo do comparativo — mas esse modelo foi desativado.
3. Tentamos `llama-3.3-70b-versatile`, documentado como modelo de produção
   da Groq — mas não estava disponível na conta usada pelo grupo (o
   catálogo liberado varia por conta/região; conferimos com
   `client.models.list()`).
4. Dos modelos realmente liberados na conta (`openai/gpt-oss-20b`,
   `openai/gpt-oss-120b`, `qwen/qwen3.8-27b`, mais os de áudio e
   segurança, que não servem aqui), o `gpt-oss-20b` tem um bug conhecido
   de tool calling nessa hospedagem (vaza um token de controle interno,
   `<|channel|>commentary`, dentro do nome da ferramenta). O `qwen/qwen3.8-27b`
   rodou os 4 tool calls do caso simples (C001) sem erro, com uma resposta
   final coerente em português — por isso é o escolhido.

Isso é um exemplo real do risco de amarrar a decisão a um nome de modelo
específico de um provedor de terceiros: o eixo de comparação (custo, tool
calling, latência) segue válido para a família Groq, mas tanto o
identificador quanto a disponibilidade por conta mudaram várias vezes
depois da decisão original — por isso registramos aqui a sequência
completa, em vez de só editar o nome como se sempre tivesse sido esse. A
lição prática: antes de fixar um modelo de terceiro no código, rodem
`client.models.list()` na própria chave para confirmar o que está
realmente disponível, em vez de confiar só na documentação pública do
provedor.

Mudaríamos de ideia se: (a) a verificação mínima mostrar o
`qwen/qwen3.8-27b` errando sistematicamente a classificação nos casos de
divergência (C002) — aí testaríamos `openai/gpt-oss-120b` (o gpt-oss maior,
que pode não ter o mesmo bug do 20b) ou migraríamos para GPT-4o mini,
aceitando ter que gerenciar cobrança; ou (b) o limite de requisições por
minuto da Groq se mostrar baixo demais para o volume de teste do grupo —
aí tentaríamos o Mistral Small de novo, desta vez já sabendo que é preciso
ativar o Pay-as-you-go antes de testar.
## 5. Credencial, gasto e dados no provedor

Registrado aqui porque o *model card* (§3, §5) e o README apontam para esta seção. Fonte: documentação da Groq consultada pelo grupo no exercício da Aula 12 (`exercicios/model-card.md`), links em `docs/fontes.md`.

- **Credencial:** no nível gratuito, a chave de API da Groq vale para a conta inteira; não há escopo granular por modelo ou recurso. O controle possível é operacional (rotacionar e revogar a chave se vazar) e, desde a Parte 3, o controle C2: a chave só é enviada a hosts da lista (`docs/seguranca.md`).
- **Gasto:** a conta é do nível gratuito, sem cartão cadastrado; o teto de gasto configurável (https://console.groq.com/docs/spend-limits) só existe em planos pagos. Sem forma de pagamento, a execução não gera cobrança; o limite efetivo é o de requisições por minuto. Falta conferir no console que nenhum cartão foi adicionado (LACUNA L3 do *model card*).
- **Dados:** por padrão a Groq não retém dado de inferência; a exceção é monitoramento de confiabilidade e abuso, por até 30 dias, em servidores nos EUA (https://console.groq.com/docs/your-data).
- **Retenção dos nossos registros:** 30 dias para logs e traces locais (`scripts/limpar_logs_antigos.py`), alinhado à janela do provedor: depois de 30 dias não sobra, em nenhum dos dois lados, registro da conversa que permita reconstruir uma decisão — o que é aceitável para um protótipo com dados sintéticos e teria de ser revisto com dado real.
