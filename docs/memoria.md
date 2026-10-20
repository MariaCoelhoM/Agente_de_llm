# Memória

Implementação em `src/memoria.py`. O desenho está em `exercicios/Memória — Agente de Suporte Técnico Doméstico.pdf` (Exercício 8).

## 1. Os dois níveis e a fronteira entre três estruturas

### 1.1 O que ocupa cada célula no case

| | curto prazo | longo prazo |
|---|---|---|
| o que é | a execução de um atendimento | o que atravessa atendimentos do mesmo contrato |
| conteúdo | prompt do sistema e memória procedural, contrato e data, mensagem do cliente, trajetória (ferramentas e resultados), trechos recuperados do manual, bloco de memória | episódica, semântica, procedural |
| persistido como | checkpoint (`dados/checkpoints.db`) | tabelas `episodica`, `semantica`, `descartes` em `dados/memoria.db` e o texto `procedural.md` |
| ciclo de vida | morre com a execução | acumula, com decaimento e remoção (§4) |

**O que precisa estar no checkpoint para a execução ser retomável sem reaplicar efeito colateral.** Os campos `visita_proposta` (data, `tool_call_id`, chave), `mensagens` (incluindo a chamada de ferramenta que espera resposta), `trajetoria`, `passos_ferramenta`, `voltas`, `tokens`, `segundos_ativos`, `contrato` e `hoje`. O reinício da conexão já aconteceu no nó `ferramentas` e está registrado em `trajetoria` e `mensagens`, então a retomada não o repete. O nó `aprovacao` roda de novo do começo na retomada, e por isso só lê o estado antes do `interrupt`. O agendamento acontece uma vez, no nó `agendar`, com chave idempotente.

**Ordem de descarte quando o contexto não cabe.**

| Fonte | Política |
|---|---|
| prompt do sistema, memória procedural, contrato, data, mensagem do cliente | nunca saem |
| resultados de ferramenta e respostas do modelo da execução | nunca saem; o teto de 12000 tokens encerra a execução (`tokens_esgotados`, encaminha para humano) antes de qualquer corte |
| trechos do manual | limitados por k=3; não são truncados |
| bloco de memória de longo prazo | **sai primeiro**: episódios do mais antigo para o mais recente, até caber em 500 tokens (`montar_contexto`) |

O último valor é o único corte que o código aplica. `config.ORCAMENTO_TOKENS` declara também limites para `system_prompt`, `ultimo_resultado`, `trajetoria` e `trechos_rag`, mas só `memoria_longo_prazo` é aplicado; os demais são metas declaradas, e o limite real da janela é o teto de tokens da execução. Nada é truncado no fim: o conteúdo mais recente nunca é cortado.

### 1.2 Checkpoint, memória e RAG neste case

| | checkpoint | memória | RAG |
|---|---|---|---|
| escopo | uma execução (`thread_id` `contrato:uuid8`) | todos os atendimentos do contrato | nenhum, é externo |
| propósito | retomar a pausa de aprovação | lembrar o que aconteceu antes | consultar manuais e políticas |
| forma | estado íntegro, com os argumentos de cada passo | um episódio e o último sinal | trechos de documentos curados |
| leitura | no início da retomada | no nó `carregar_memoria`, por relevância ao relato | quando o modelo chama a ferramenta |
| quem escreve | o framework, a cada passo | o código, no fim do atendimento | ninguém: o corpus é curado |

**O que a recuperação por relevância traz que a serialização integral não traria.** Do histórico do contrato entram só os episódios parecidos com o relato de agora (BM25 dentro do contrato, até 3) e o último sinal, em até 500 tokens. Serializar todos os atendimentos passados traria os argumentos de cada chamada e todas as mensagens do modelo, e o prompt cresceria a cada atendimento.

**O que ela deixa para trás.** O texto exato das respostas passadas e os argumentos das chamadas. E, por ser lexical, episódios cujo relato usou outras palavras: um relato sem palavra em comum cai para o episódio mais recente do mesmo contrato.

## 2. As três memórias

| Memória | O que guarda | Estrutura | Por que essa estrutura |
|---|---|---|---|
| semântica | `ultimo_sinal_dbm` do contrato | chave-valor, tabela `semantica` | o acesso é por chave exata; buscar o sinal por similaridade seria caro e impreciso |
| episódica | um resumo por atendimento: sintoma, causa, ação, resultado | tabela `episodica`, lida por BM25 dentro do contrato | o relato é texto livre e a pergunta é "já vimos algo parecido?" |
| procedural | quatro regras curtas aprendidas na operação | texto em `src/prompts/procedural.md`, no prompt de toda execução | as regras valem sempre, então não há o que recuperar |

## 3. A política de escrita

**O código extrai por regra**, no nó `registrar_memoria`, no fim do atendimento. O modelo não decide o que vira memória: o que entra vem do que as ferramentas devolveram (`extrair_episodio`), e o que o cliente apenas afirmou não vira fato. Atendimento com contrato inexistente não grava nada. O preço da escolha é que a regra não prevê o que não foi escrito nela: uma causa nova cai em `sem_causa_identificada`.

**Volume por execução**, medido em `python -m scripts.demo_remocao`: um episódio (286 caracteres) e um fato, `ultimo_sinal_dbm` (82 caracteres), ou seja, 2 registros e cerca de 370 caracteres por atendimento. Sem teste de linha bem-sucedido, só o episódio.

**Idempotência.** A chave de cada registro deriva do conteúdo (contrato, chave, valor e data). Gravar o mesmo fato duas vezes devolve `ja_existia=True` e não cria outra linha.

## 4. As três causas de esquecimento

O case escolhe as três, cada uma por uma razão de domínio.

| Causa | O que faz no sistema | O dado é apagado? | Quando decide |
|---|---|---|---|
| contradição | dois valores para a mesma chave: vence o de `vigente_desde` mais recente; o perdedor vai para `descartes` com o motivo. Um fato antigo que chega depois não vence | não | na leitura, pelo carimbo de tempo |
| decaimento | episódio com mais de 180 dias é rebaixado (`ativo=0`) | não, só rebaixado | no início de cada atendimento |
| remoção | `remover_titular` apaga o contrato | sim | sob demanda |

**Decaimento.** O corte de 180 dias é um valor do projeto, não uma medida: o que se guarda são relatos e causas de um cliente residencial, e um episódio com mais de seis meses descreve uma instalação que pode ter mudado numa visita ou numa troca de equipamento. Rebaixa em vez de apagar porque o custo de manter é pequeno e o dado continua auditável.

**Remoção, e a cobertura.** O dado do titular sai de todas as estruturas em que foi gravado:

| Estrutura | O que a remoção faz |
|---|---|
| tabela `semantica` | apaga as linhas do contrato |
| tabela `descartes` | apaga as linhas do contrato |
| tabela `episodica` | apaga as linhas do contrato |
| checkpoints (`checkpoints` e `writes`) | apaga as linhas com `thread_id` iniciado por `contrato:` |
| logs em `logs/` | apaga os arquivos cujo campo `contrato` é o do titular |
| memória procedural | não guarda titular: é texto curado por pessoas, e a varredura confere os `.md` |
| `dados/provedor.db` | fora do alcance: é a fonte de verdade do provedor, não memória do agente |
| backups externos | fora do alcance |

**Verificação, em outro programa.** `scripts/varrer_contrato.py` não usa o código de remoção: percorre o projeto procurando o contrato em qualquer coluna de qualquer banco `.db` e em arquivos `.json`, `.md` e `.txt`. `python -m scripts.demo_remocao` roda o procedimento do enunciado, sem modelo e numa pasta temporária. Saída:

```
1. gravar
   volume de escrita de um atendimento: semantica 1 registro(s), 82 caracteres; episodica 1 registro(s), 286 caracteres
2. o comportamento mudou?
   prompt do 2o atendimento traz o histórico do cliente: True
3. varrer antes de remover
   8 ocorrência(s)
     dados/memoria.db: semantica.contrato (1)
     dados/memoria.db: episodica.contrato (2)
     dados/checkpoints.db: checkpoints.thread_id (22)
     dados/checkpoints.db: checkpoints.checkpoint (10)
     dados/checkpoints.db: writes.thread_id (85)
     dados/checkpoints.db: writes.value (10)
     logs/demo_2.json
     logs/demo_1.json
4. remover
   {'semantica': 1, 'descartes': 0, 'episodica': 2, 'checkpoints': 107, 'logs': 2}
5. o comportamento voltou?
   memória devolve vazio: True
6. varrer depois de remover
   0 ocorrência(s)
```

O passo 3 mostra que o contrato estava em dois bancos (`memoria.db` e `checkpoints.db`) e em dois logs; o passo 6 mostra zero.

**O que a remoção não cobre.** `docs/io.md` é gerado a partir dos logs e cita contratos e mensagens. Os contratos do projeto são sintéticos; com dado real, o arquivo teria de ser regenerado depois da remoção.

## 5. A conversa

**O que identifica uma conversa.** O `thread_id` é `contrato:uuid8` (`src/agent.py`). Mesmo `thread_id`, mesma conversa; chave nova, histórico vazio. Como o uuid é gerado a cada execução, cada atendimento começa com histórico de conversa vazio.

**Duas conversas ao mesmo tempo do mesmo contrato.** Ganham dois `thread_id` diferentes, com checkpoints, logs e trajetórias independentes: nenhuma enxerga a outra. Elas compartilham a memória de longo prazo, que é por contrato. As escritas se reconciliam pelas regras da §3 e da §4: a chave derivada do conteúdo evita duplicata, o carimbo de tempo resolve contradição, e a visita para a mesma data é idempotente (`docs/humano.md` §5).

**Onde o checkpoint é gravado.** Em arquivo: `SqliteSaver` sobre `dados/checkpoints.db`. Os testes usam `InMemorySaver`, e nesse caso a conversa morre com o processo, o que vale só para os testes.

**O que acontece quando a janela enche.** Não há truncamento nem sumarização. O orçamento (6 voltas, 8 chamadas de ferramenta, 12000 tokens, 120 s) encerra a execução e encaminha para um atendente antes de a janela encher, e o case prevê atendimentos de 3 a 5 mensagens. O que se perde é a execução inteira: o cliente vai para um humano, com o que já foi verificado. Sumarizar o trecho antigo exigiria uma chamada de modelo a mais e arriscaria perder um resultado de ferramenta de que o código depende.

**O que passa da conversa para a memória de longo prazo.** Um episódio (o relato inicial do cliente, a causa, a ação e o resultado, extraídos por regra) e o último sinal medido. O resto da conversa, incluindo as respostas do modelo, não sobrevive.

## 6. Orçamento do bloco de memória

O bloco entra no prompt com teto de 500 tokens (`config.ORCAMENTO_TOKENS`). Se estourar, o episódio mais antigo sai primeiro. O bloco é marcado como "não confirmado pelo cliente agora", e o prompt manda confirmar com as ferramentas.

## 7. Limites

- A estimativa de tokens é por caracteres (4 por token), sem tokenizador.
- Backups externos não são alcançados pela remoção.
- A recuperação episódica é lexical: um relato com outras palavras cai para o episódio mais recente do mesmo contrato.
- A regra de extração só reconhece as causas que prevê.
- Os limites de `ORCAMENTO_TOKENS` diferentes de `memoria_longo_prazo` não são aplicados (§1.1).
