# Arquitetura do sistema (Parte 2)

## 1. Visão geral

Um grafo LangGraph com estado tipado. O modelo decide só o que o modelo sabe decidir: qual ferramenta chamar e como falar com o cliente. O código decide o resto: o que é permitido, quanto custa continuar, o que vira memória, o que é fonte válida e quando uma pessoa precisa aprovar.

Há um único nó que chama o modelo (`agente`). Todos os outros nós, e todas as arestas condicionais, são código.

## 2. Diagrama

Legenda: `[M]` o nó chama o modelo. `[C]` o nó é código. `(c)` aresta condicional, decidida por regra em código. `==>` aresta incondicional. `##` ponto em que o sistema para e espera uma pessoa.

```
 mensagem + contrato (da sessão)
          |
          v
   +--------------+   (c) mensagem vazia
   | entrada  [C] |------------------------------------------+
   +--------------+                                          |
          | (c) segue                                        |
          v                                                  |
   +------------------+                                      |
   | carregar_memoria |  lê semântica, episódica, procedural |
   |             [C]  |  (SQLite memoria.db, BM25 no contrato)|
   +------------------+                                      |
          ==>                                                |
          v                                                  |
   +--------------+  (c) cobrança/cancelamento/atendente     |
   | triagem  [C] |----------------------------------------->+
   +--------------+  (c) sem palavra de sintoma ----+        |
          | (c) suporte                             |        |
          v                                         |        |
   +--------------+  (c) estouro de orçamento       |        |
   |              |  ou erro fatal do modelo        |        |
   | agente   [M] |-------------------------------->+------->+
   |              |<--------------------+           |        |
   +--------------+                     |           |        |
      | (c) pediu ferramenta             |           |        |
      v                                  | (c) volta |        |
   +--------------+  (c) laço, teto de   | ao agente |        |
   | ferramentas  |  passos               |           |        |
   |         [C]  |---------------------->+---------->+        |
   +--------------+                       |           |        |
      | (c) propor_visita válida          |           |        |
      v                                   |           |        |
   +--------------+                       |           |        |
   | aprovacao [C]|  ## PAUSA: interrupt  |           |        |
   +--------------+  espera o cliente     |           |        |
          ==>                             |           |        |
          v                               |           |        |
   +--------------+  (c) expirou -------->+---------->+        |
   | agendar  [C] |  (c) aprovou/rejeitou: volta ao agente    |
   +--------------+                                            |
                                                               v
   agente --(c) respondeu sem ferramenta--> finalizar   +-------------------+
                                                 ^      | encaminhar_humano |
                                                 |      |              [C]  |
                                                 +<==== +-------------------+
          finalizar [C]: valida fontes e contrato de saída (Pydantic)
          ==> registrar_memoria [C]: grava memória por regra ==> FIM

 Ferramentas (chamadas pelo nó `ferramentas`, nunca pelo modelo direto no banco):
   obter_data_atual, testar_linha, conferir_queda_bairro   leitura
   reiniciar_conexao                                        escrita reversível
   propor_visita                                            validação pura, sem escrita
   consultar_base_conhecimento                              leitura; índice BM25 sobre dados/corpus
 Fora do alcance do modelo:
   agendar_visita_tecnico   escrita irreversível; só o nó `agendar` chama, depois da pessoa
 Armazenamentos: provedor.db (clientes, modems, visitas), memoria.db, checkpoints.db (SQLite)

 Condições de parada: ver §4.5 (11 motivos). Todo caminho passa por finalizar.
```

## 3. Mapa de arquivos

| Arquivo | Papel |
|---|---|
| src/grafo.py | nós, arestas e condições; `obter_grafo` compila uma vez |
| src/estado.py | estado tipado e reducers |
| src/guardas.py | taxonomia de términos, orçamento, laço, validação de data |
| src/llm.py | fronteira com o modelo, tentativas, LLMSimulado para testes |
| src/tools.py, src/db.py | ferramentas e SQLite do provedor (idempotência, migração) |
| src/rag.py | BM25, corte, portão de suficiência |
| src/memoria.py | três memórias, escrita por regra, remoção |
| src/schemas.py | contrato de saída (Pydantic) |
| src/agent.py | executa o grafo, trata a pausa, grava o log |
| src/prompts/ | suporte_v2.md e procedural.md, carregados em tempo de execução |
| conferir_grafo.py | imprime nós e arestas do grafo que o sistema executa |

## 4. As seis perguntas

### 4.1 As ferramentas

| Ferramenta | O que faz | Tipo | Reversível |
|---|---|---|---|
| obter_data_atual | devolve a data de hoje | leitura | não se aplica |
| testar_linha | lê status e sinal (dBm) do modem do contrato | leitura | não se aplica |
| conferir_queda_bairro | lê se o bairro do cliente está em manutenção | leitura | não se aplica |
| consultar_base_conhecimento | busca trechos nos manuais; devolve `suficiente=false` se nada cobre | leitura | não se aplica |
| reiniciar_conexao | recoloca o modem em ONLINE e soma um reinício; recusa se o sinal é igual ou pior que -27 dBm | escrita | sim |
| propor_visita | valida data (hoje até amanhã), contrato e bairro; não escreve nada | validação | não se aplica |
| agendar_visita_tecnico | cria a visita; idempotente por (contrato, data) | escrita | **não**: desloca um técnico |

O modelo não tem `agendar_visita_tecnico` na lista de ferramentas. `propor_visita` só guarda a proposta no estado. Quem agenda é o nó `agendar`, que passa `confirmado_pelo_cliente=True` depois da resposta da pessoa.

O contrato nunca é digitado pelo modelo: o grafo injeta o contrato da sessão nos argumentos de `testar_linha`, `conferir_queda_bairro` e `reiniciar_conexao`, e substitui o que o modelo tiver escrito (registrado como `contrato_sobrescrito`).

### 4.2 O laço

A cada volta, o nó `agente` monta as mensagens (prompt do sistema, contrato e data, memória procedural, contexto de longo prazo, conversa) e chama o modelo uma vez. Se a resposta traz pedidos de ferramenta, a aresta leva ao nó `ferramentas`, que executa cada um em sequência, registra o resultado na trajetória e devolve ao `agente`. Se a resposta não traz ferramenta, o motivo vira `resposta_final` e a execução segue para `finalizar`.

A volta seguinte existe porque o modelo pediu ferramenta e nenhum limite foi atingido. Antes de cada chamada ao modelo, `guardas.verificar_orcamento` confere voltas, tokens e tempo.

### 4.3 O estado

Tudo que o código precisa para decidir é campo explícito de `EstadoAtendimento` (§7). A lista `mensagens` guarda só a conversa no formato do modelo. Contadores, decisões, rota, motivo de parada e proposta de visita não ficam nela.

### 4.4 O orçamento

| Teto | Valor | Onde é verificado |
|---|---|---|
| chamadas ao modelo por atendimento | 6 | `verificar_orcamento`, antes de cada chamada |
| chamadas de ferramenta por atendimento | 8 | nó `ferramentas` |
| testes de linha por atendimento | 3 | nó `ferramentas` (regra do domínio) |
| tokens acumulados | 12000 | `verificar_orcamento` |
| tempo de máquina | 120 s, sem contar a espera humana | `verificar_orcamento` |
| mesma ferramenta e mesmos argumentos | 3 vezes sem escrita no meio | `detectar_laco` |
| passos do grafo | 25 (`RECURSION_LIMIT`, declarado) | LangGraph, tratado em `agent.py` |
| espera da aprovação | 900 s | `PRAZO_APROVACAO_SEGUNDOS` |

O teto de testes de linha devolve um erro como dado ao modelo e a execução continua. Os demais encerram a execução.

### 4.5 O término

Toda execução acaba com um `motivo_parada`, definido em `src/guardas.py`:

| Motivo | Quando | Encaminha para humano |
|---|---|---|
| resposta_final | o modelo respondeu sem pedir ferramenta | não |
| entrada_incompleta | a mensagem não cita nenhum sintoma; o sistema pede detalhes sem chamar o modelo | não |
| encaminhado_humano | a triagem achou cobrança, cancelamento ou pedido de atendente, ou a mensagem veio vazia | sim |
| limite_de_voltas | mais de 6 chamadas ao modelo | sim |
| limite_de_ferramentas | mais de 8 chamadas de ferramenta | sim |
| laco_detectado | mesma ferramenta e mesmos argumentos 3 vezes | sim |
| tempo_esgotado | mais de 120 s de tempo de máquina | sim |
| tokens_esgotados | mais de 12000 tokens | sim |
| aprovacao_expirada | o cliente não respondeu em 900 s | sim |
| erro_fatal_llm | erro do modelo que repetir não resolve | sim |
| recursion_limit | o grafo passou de 25 passos | sim |

Erros recuperáveis do modelo (limite de taxa, rede, timeout) têm até 3 tentativas. Qualquer outro erro é fatal. Quando a resposta é `resposta_final` mas falta fonte verificável, o campo `suficiente` do contrato de saída fica falso (`sem_fonte`, `citacao_nao_verificada` ou `fora_do_corpus`), e o motivo de parada continua `resposta_final`.

### 4.5.1 O humano

O sistema chama o próprio cliente, e não um atendente: a pessoa que sabe se a data serve e que arca com a visita. Ela vê a ação (`agendar_visita_tecnico`), o contrato, a data proposta, a consequência (desloca um técnico, tem custo, não é desfeito sozinho), as opções (aprovar, rejeitar, editar) e a janela de edição (de hoje até 14 dias). Detalhes em `docs/humano.md`.

Se ela não responde em 900 s, a decisão vira `expirou`: nada é agendado, o motivo é `aprovacao_expirada` e o cliente recebe um texto dizendo que nada foi agendado e que será encaminhado a um atendente. Uma resposta fora do formato vira `rejeitar`. Uma data editada fora da janela também vira `rejeitar`.

## 5. A defesa do nível de autonomia

O nível é **agente com portões**: um laço em que o modelo escolhe a próxima ferramenta, cercado por regras em código que limitam o que ele pode fazer.

A decisão que só o modelo toma em tempo de execução é **qual diagnóstico rodar, em que ordem e quando parar, a partir de texto livre**. Os logs de `docs/io.md` mostram isso com o mesmo prompt e entradas diferentes:

| Caso | Ferramentas que o modelo escolheu |
|---|---|
| caso_C001_feliz ("luz piscando vermelha e a internet caiu") | testar_linha, conferir_queda_bairro, reiniciar_conexao, testar_linha |
| caso_C005_nao_agenda ("quero que mandem um técnico hoje") | testar_linha, conferir_queda_bairro, e parou: bairro em manutenção |
| caso_entrada_ambigua ("não sei se é o wifi ou a internet") | só testar_linha, e propôs um teste com cabo |
| caso_C004_pausa_edita ("a luz está vermelha") | testar_linha, obter_data_atual, propor_visita |
| caso_fora_do_corpus (abrir portas no roteador) | só consultar_base_conhecimento |

Por que um nível abaixo não servia: um **workflow** fixo rodaria os mesmos passos para todo cliente, o que reiniciaria conexões que não precisavam de reinício e consultaria o manual em perguntas que não pedem manual. Um **roteador** classificaria o assunto, mas a escolha seguinte depende do resultado da ferramenta anterior (sinal, manutenção no bairro, reinício que resolve ou não), e isso muda a cada execução.

Limite desta defesa: parte dessa árvore é verificável por regra (sinal igual ou pior que -27 dBm significa falha física; bairro em manutenção bloqueia visita). Essas regras já estão em código, nas ferramentas e no nó `ferramentas`. O que sobra para o modelo é interpretar o relato em texto livre e escolher o próximo diagnóstico. Se o domínio tivesse só os casos de sinal e manutenção, um workflow bastaria.

## 6. O grafo

### 6.1 Nós

| Nó | O que faz | Chama o modelo |
|---|---|---|
| entrada | fixa a data de hoje, zera contadores, coloca a mensagem do cliente na conversa; mensagem vazia vira `encaminhado_humano` | não |
| carregar_memoria | aplica o decaimento e monta o contexto de longo prazo do contrato | não |
| triagem | classifica por regex em texto sem acento: cobrança e afins vão para humano, mensagem sem sintoma pede detalhes, o resto vai para o agente | não |
| agente | confere o orçamento e chama o modelo uma vez | **sim** |
| ferramentas | executa os pedidos de ferramenta, injeta o contrato, detecta laço, aplica os tetos, guarda a proposta de visita | não |
| aprovacao | pausa o grafo com `interrupt` e valida a resposta da pessoa | não |
| agendar | única chamada a `agendar_visita_tecnico`; devolve o resultado ao modelo como mensagem de ferramenta | não |
| encaminhar_humano | escolhe o texto fixo conforme o motivo | não |
| finalizar | valida fontes e citações, monta e valida `RespostaAtendimento` | não |
| registrar_memoria | grava memória semântica, episódica e procedural por regra | não |

### 6.2 Os padrões

| Padrão | Onde, no grafo | Por que ele, e não o de baixo | Condição de não uso |
|---|---|---|---|
| sequencial com portão | `entrada -> carregar_memoria -> triagem`, e `finalizar -> registrar_memoria` | o trecho é fixo e cada passo é verificável por regra; usar o modelo aqui custaria uma chamada e erraria | se o assunto passasse a exigir julgamento sobre texto livre |
| *router* | `triagem`, com três rotas (humano, incompleta, suporte) | as rotas são poucas e se reconhecem por palavra; regex custa zero e não erra por variação | se as rotas viessem de assunto sem palavra-chave, caberia embedding |
| paralelização | não usado | as ferramentas de uma volta dependem uma da outra (o reinício depende do sinal) e o provedor atende uma requisição por vez | se houvesse diagnósticos independentes e lentos |
| orquestrador-trabalhador | não usado | há um domínio só e um agente só | se o sistema crescesse para mais de um domínio |
| avaliador-otimizador | não usado | `finalizar` valida por código e não manda o modelo reescrever; a recusa por falta de fonte é uma resposta fixa | se a qualidade do texto passasse a ser critério de aceite |
| agente (laço) | `agente <-> ferramentas` | defendido na §5: a escolha da próxima ferramenta depende do resultado da anterior e do texto livre | se os casos se reduzissem aos de sinal e manutenção |

### 6.3 Quem decide cada bifurcação

| Aresta condicional | Degrau | Regra |
|---|---|---|
| entrada -> carregar_memoria \| encaminhar_humano | regra em código | `motivo_parada` preenchido (mensagem vazia) |
| triagem -> agente \| encaminhar_humano \| finalizar | regra em código | regex de cobrança; regex de sintoma |
| agente -> ferramentas \| finalizar \| encaminhar_humano | regra em código | `motivo_parada` (o código o preenche a partir de haver ou não pedido de ferramenta) |
| ferramentas -> aprovacao \| agente \| encaminhar_humano | regra em código | `visita_proposta` preenchida; ou `motivo_parada` de teto ou laço |
| agendar -> agente \| encaminhar_humano | regra em código | decisão `expirou` |

Nenhuma aresta usa embedding nem modelo como roteador, então não há saída `Literal`. O modelo influencia o caminho de um jeito só: pedir ou não uma ferramenta. A aresta lê esse fato, mas quem a decide é uma regra.

### 6.4 Conferência contra o desenho

`conferir_graf.py`, na raiz, importa `obter_grafo` de `src/grafo.py`, a mesma função que `src/agent.py` usa, e imprime nós e arestas do grafo compilado. O modelo e o checkpointer passados a ele não afetam a topologia.

Comando:

```
python conferir_grafo.py
```

Saída:

```
NÓS
  __start__
  entrada
  carregar_memoria
  triagem
  agente
  ferramentas
  aprovacao
  agendar
  encaminhar_humano
  finalizar
  registrar_memoria
  __end__
ARESTAS
  __start__ -> entrada
  agendar -> agente   [condicional]
  agendar -> encaminhar_humano   [condicional]
  agente -> encaminhar_humano   [condicional]
  agente -> ferramentas   [condicional]
  agente -> finalizar   [condicional]
  aprovacao -> agendar
  carregar_memoria -> triagem
  encaminhar_humano -> finalizar
  entrada -> carregar_memoria   [condicional]
  entrada -> encaminhar_humano   [condicional]
  ferramentas -> agente   [condicional]
  ferramentas -> aprovacao   [condicional]
  ferramentas -> encaminhar_humano   [condicional]
  finalizar -> registrar_memoria
  triagem -> agente   [condicional]
  triagem -> encaminhar_humano   [condicional]
  triagem -> finalizar   [condicional]
  registrar_memoria -> __end__
```

São 12 nós (contando início e fim) e 19 arestas. Todas as arestas do diagrama da §2 aparecem na lista. O diagrama desenha o retorno `agente <- ferramentas` e o retorno `agendar -> agente`, que na lista são `ferramentas -> agente` e `agendar -> agente`. Se o desenho e a lista divergirem, vale a lista.

## 7. O estado

### 7.1 Os campos

| Campo | Tipo | Quem escreve | Quem lê | De onde veio |
|---|---|---|---|---|
| thread_id | str | `agent.py` (entrada do grafo) | checkpointer, log | gerado: `contrato:uuid8` |
| contrato | str | `agent.py` | ferramentas, agendar, carregar_memoria, registrar_memoria, agente (prompt) | a sessão, não o modelo |
| mensagem | str | `agent.py` | entrada, triagem, carregar_memoria, registrar_memoria | texto do cliente |
| hoje | str | entrada | carregar_memoria, ferramentas, aprovacao, agente (prompt), registrar_memoria | relógio do sistema |
| mensagens | lista, reducer soma | entrada, agente, ferramentas, agendar | agente | cliente, modelo e resultados de ferramenta |
| trajetoria | lista, reducer soma | todos os nós, cada um com o que é seu | ferramentas (laço, testes), finalizar, registrar_memoria, log | eventos do que aconteceu |
| tokens | int, reducer soma | agente | verificar_orcamento, log | uso informado pelo provedor |
| segundos_ativos | float, reducer soma | agente | verificar_orcamento | tempo medido em volta de cada chamada |
| memoria_contexto | str | carregar_memoria | agente (prompt) | memoria.db |
| rota | str | triagem | aresta após a triagem | regra de triagem |
| voltas | int | entrada (zera), agente | verificar_orcamento, log | contador |
| passos_ferramenta | int | entrada (zera), ferramentas | verificar_orcamento | contador |
| visita_proposta | dict ou None | entrada (zera), ferramentas, agendar (limpa) | aresta após ferramentas, aprovacao, agendar | `propor_visita` válida |
| decisao_humana | dict ou None | entrada (zera), aprovacao | agendar | resposta da pessoa, já validada |
| motivo_parada | str ou None | entrada, triagem, agente, ferramentas, agendar | arestas, encaminhar_humano, finalizar | regras de término |
| resposta_texto | str ou None | triagem, agente, encaminhar_humano | finalizar | modelo ou texto fixo |
| saida | dict ou None | finalizar | agent.py | contrato de saída validado |

Há campos sem reducer escritos por mais de um nó (`voltas`, `passos_ferramenta`, `visita_proposta`, `motivo_parada`, `resposta_texto`). Nenhum deles é escrito em ramos paralelos: o grafo é sequencial, então cada escrita acontece em um passo próprio e a substituição é a regra certa. Se um dia houver nós paralelos, esses campos precisam de reducer. A §7.2 mostra o que ocorre sem ele.

### 7.2 Os reducers

| Campo | Reducer | Por quê |
|---|---|---|
| mensagens | soma de listas | cada nó entrega só as mensagens novas |
| trajetoria | soma de listas | vários nós acrescentam eventos; nenhum pode apagar o dos outros |
| tokens | soma | o orçamento é o total acumulado |
| segundos_ativos | soma | idem, em tempo |

Demonstração: `python -m scripts.demo_reducer` monta um grafo de teste com dois nós paralelos escrevendo no mesmo campo. Sem reducer, o LangGraph 1.2.16 levanta `InvalidUpdateError` ("Can receive only one value per step"). Com `operator.add`, as duas escritas se somam. A saída do script está em `docs/grafo.md` §7.

### 7.3 O que não está no estado

**Na lista de mensagens, e só nela:** o texto da conversa (mensagem do cliente, resposta do modelo, resultado de cada ferramenta). É conteúdo que o modelo precisa reler.

**Derivado e não guardado:**

| Valor | De onde se recalcula | Por que não guardar |
|---|---|---|
| quantos testes de linha já houve | conta na trajetória | um contador seria uma segunda fonte de verdade |
| se há laço | `detectar_laco` sobre a trajetória | idem |
| as fontes da resposta | `finalizar` percorre a trajetória | fonte só vale se a ferramenta rodou sem erro naquela execução |
| se encaminha para humano | tabela de motivos em `guardas.py` | decorre do motivo de parada |
| se a proposta de visita é válida | `_validar_proposta` na hora | depende do resultado do teste de linha na mesma execução |

### 7.4 O estado entre agentes

O sistema tem um agente só. Não há estado passado entre agentes.

## 8. O que mudou em relação à Parte 1

| Antes | Agora |
|---|---|
| laço while no agent.py | grafo com nós e arestas condicionais |
| confirmação por varredura da palavra "sim" | `interrupt`: o modelo não tem a ferramenta que agenda |
| contrato digitado pelo modelo nas chamadas | contrato da sessão, que substitui o do modelo |
| resposta em texto livre | saída validada com fontes e suficiência |
| sem conhecimento de domínio | RAG sobre manuais e políticas |
| sem memória entre atendimentos | memória semântica, episódica e procedural |
| prompt dentro do código | src/prompts/, com versão registrada no log |

## 9. Contrato de saída

`RespostaAtendimento` exige `resultado`, `fontes` e `suficiente`. Regras aplicadas em código no nó `finalizar`:

- `suficiente=true` exige ao menos uma fonte: ferramenta que rodou sem erro, ou trecho do corpus citado e de fato recuperado naquela execução;
- uma citação de id que a ferramenta não devolveu é separada em `citacoes_invalidas` e não vira fonte;
- se o modelo consultou o manual, o portão barrou e não há outra fonte, o texto do modelo é substituído por uma recusa fixa, com `suficiente=false` e `encaminhar_humano=true`. A recusa faz parte do contrato.

## 10. Fluxo de um atendimento com visita

A mensagem e o contrato entram. A triagem libera. O modelo chama `testar_linha` e vê falha física, chama `obter_data_atual` e `propor_visita`. O grafo pausa. A pessoa responde. `agendar` executa e devolve o resultado como mensagem de ferramenta. O modelo escreve a resposta com o que de fato aconteceu. `finalizar` valida e `registrar_memoria` grava. O log JSON é escrito com commit, modelo, temperatura, prompts em uso, trajetória e saída.

## 11. Segurança

O `.env` nunca é versionado (`.gitignore`). A chave do Groq fica só nele. Dados pessoais no log são só o contrato e a mensagem do cliente. A remoção por titular está em `docs/memoria.md`. Retenção e escopo de chave estão no model card.
