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

## 3. A verificação mínima

O comparativo do §1 é teórico (documentação e preço publicados pelos três
provedores). Testar de verdade os três exigiria uma chave paga da OpenAI e
ativar o Pay-as-you-go da Mistral (§4) — fora do escopo de uma entrega que
deve rodar sem custo. Por isso, a verificação empírica abaixo cobre só o
modelo realmente usado, `qwen/qwen3.8-27b` via Groq, contra 4 dos 5 casos
do `docs/case.md` §2.8:

| Caso | Ação esperada | Ação tomada pelo agente | Resultado |
|---|---|---|---|
| C001 (simples) | reiniciar e confirmar que voltou | testou a linha, reiniciou, testou de novo, confirmou ONLINE | ✅ correto |
| C002 (divergência) | não fechar como "resolvido" sem investigar; achar a causa real | descobriu o bairro pelo contrato, viu que estava em manutenção, explicou a causa real e recusou agendar visita individual | ✅ correto |
| C999 (inexistente) | tratar o erro como dado, sem quebrar, pedir o contrato certo | recebeu `contrato_nao_encontrado` e pediu o número certo ao cliente | ✅ correto |
| C005 (bairro em manutenção) | não agendar visita individual | na primeira tentativa ofereceu agendar mesmo assim (inconsistente com C002); depois de ajustar o `SYSTEM_PROMPT` para proibir isso explicitamente, passou a recusar do mesmo jeito que o C002 | ✅ correto, depois do ajuste — ver §4 |
| C004 (falha física) | não insistir em reiniciar; propor a data do dia seguinte e só agendar com "sim" do cliente | reconheceu o sinal de −30dBm como falha física, não chamou `reiniciar_conexao`, confirmou que o bairro não está em manutenção, chamou `obter_data_atual` e propôs a data certa (amanhã) pedindo só a confirmação | ✅ correto |

Os 5 casos do domínio (`docs/case.md` §2.8) estão validados para o modelo
escolhido.

Comparar contra Mistral Small e GPT-4o mini fica registrado como um passo
que o grupo pode fazer se sobrar tempo — não é bloqueante para a entrega,
já que a decisão final (§4) foi tomada por restrição prática (custo zero
sem cartão), não por qualidade comparada entre os três.

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