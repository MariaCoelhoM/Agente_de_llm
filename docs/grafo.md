# O grafo e o que o framework deu

Nós, arestas, quem decide cada bifurcação e a taxonomia de términos estão em `docs/arquitetura.md` (§2, §4.5, §6). Este documento trata da implementação sobre o LangGraph 1.2.16: o que precisou ser escrito além do framework, o que ele cobriu, a decisão que virou parâmetro e a demonstração do reducer.

## 1. Implementação

O grafo é um `StateGraph(EstadoAtendimento)` montado por `construir_grafo` em `src/grafo.py`. `obter_grafo` (src/grafo.py:517) compila uma vez por combinação de modelo e checkpointer e reaproveita nas execuções seguintes do mesmo processo. `src/chat.py:169` (a `Conversa`, usada pelo chat, por `src/agent.py` e pela suíte) e `conferir_grafo.py:6` chamam a mesma função, então a conferência da §6.4 de `docs/arquitetura.md` vale para o grafo que o sistema executa.

As arestas condicionais declaram a lista de destinos. Os nós de decisão (`apos_entrada`, `apos_triagem`, `apos_agente`, `apos_ferramentas`, `apos_agendar`) leem só campos do estado e não chamam o modelo.

## 2. O que o framework não deu

| Frente | O que o framework dá | O que foi escrito | Linhas |
|---|---|---|---|
| motivo de término | o nó terminal diz que acabou, não diz por quê | tabela de motivos (`src/guardas.py:8-25`), nó `encaminhar_humano` (`src/grafo.py:398`), tratamento de `GraphRecursionError` (`src/chat.py:247-249`) | 21 |
| detector de laço | nenhum; `recursion_limit` só limita o dano | `_chave` e `detectar_laco` (`src/guardas.py:48-71`), chamada no nó `ferramentas` (`src/grafo.py:287`) | 21 |
| tetos | só o de passos do grafo | voltas, tokens e tempo em `verificar_orcamento` (`src/guardas.py:30-45`), teto de ferramentas e de testes de linha no nó `ferramentas` (`src/grafo.py:283` e `292`) | 20 |
| erro recuperável ou fatal | nenhum | `ErroLLMFatal` (`src/llm.py:11`), tentativas e classificação em `ClienteLLM.chamar` (`src/llm.py:94-114`), captura no nó `agente` (`src/grafo.py:210`) | 22 |
| **total** | | | **84** |

O detector merece uma observação. Ele conta repetições idênticas dentro do turno, desde a última escrita **diferente** da chamada atual, porque testar de novo depois de reiniciar é legítimo. (Parte 3: antes, a própria escrita repetida zerava a contagem e o reinício em série nunca era pego — defeito E2 de `docs/mudancas.md`. As linhas da tabela acima foram atualizadas para o código da Parte 3; o total de linhas é o da Parte 2.) O limite de testes de linha (3) e o de repetições (3) se sobrepõem: em quatro `testar_linha` iguais sem reinício no meio, o detector dispara antes do teto de testes. O teste `test_limite_de_testes_de_linha` afrouxa o detector para exercitar o teto de testes.

## 3. O que o framework cobriu

| Frente | Evidência de que não foi preciso escrever |
|---|---|
| pausa e retomada | `interrupt(...)` em `src/grafo.py:347` e `Command(resume=...)` em `src/chat.py:197`: duas linhas; a suspensão e a retomada do grafo são do framework |
| persistência da pausa | `SqliteSaver(self._conexao)` em `src/chat.py:168`: uma linha; o estado salvo, o `thread_id` e a retomada em outro processo são do framework |
| junção de campos | `Annotated[..., operator.add]` em `src/estado.py`: uma anotação por campo; a soma e a conferência de escrita única por passo são do framework |
| execução do grafo | `obter_grafo(...)`: compilação, ordem dos passos e roteamento pelas arestas |

## 4. A decisão que virou parâmetro: o limite de passos

**A decisão.** Quantos passos do grafo uma execução pode gastar antes de ser considerada presa.

**Como ela estava justificada.** O caminho mais longo legítimo é: 3 nós iniciais (`entrada`, `carregar_memoria`, `triagem`), até 6 visitas ao `agente`, até 6 às `ferramentas`, `aprovacao`, `agendar`, `finalizar` e `registrar_memoria`, cerca de 19 passos. O valor 25 dá folga sobre esse caminho e só estoura se um teto do orçamento falhar.

**O que o framework fez dela.** No langgraph 1.2.16 o padrão de `recursion_limit` é **10007** (`langgraph/_internal/_config.py:32`, alterável pela variável de ambiente `LANGGRAPH_DEFAULT_RECURSION_LIMIT`). Em versões anteriores o padrão era 25. O valor mudou de uma versão para outra, e quem não o declara herda o que a biblioteca trouxer.

**O que acontece se o padrão mudar numa atualização.** Sem a declaração, o último limite do sistema passaria a ser 10007 passos. Os tetos de voltas, de ferramentas, de tokens e de tempo continuariam barrando uma execução presa antes disso, mas a rede de segurança final deixaria de existir: se um deles falhasse, o grafo giraria milhares de passos antes de parar.

**A declaração.** `config.RECURSION_LIMIT = 25` (`src/config.py`), passado em cada execução (`src/chat.py:171`). O estouro vira o motivo `recursion_limit`, com encaminhamento ao humano, e não derruba o programa. O teste `test_recursion_limit_vira_motivo_de_termino` reduz o limite para 6 e confere esse caminho.

## 5. Reducers: a demonstração

`python -m scripts.demo_reducer` monta um grafo mínimo à parte, com dois nós em paralelo escrevendo o mesmo campo, uma vez com reducer e outra sem:

```
COM reducer: {'achados': ['status do bairro', 'trecho do manual']}
SEM reducer: InvalidUpdateError -> At key 'achados': Can receive only one value per step. Use an Annotated key to handle multiple values.
```

Com o reducer, as duas escritas se somam. Sem ele, o langgraph 1.2.16 recusa a segunda escrita com erro explícito, em vez de sobrescrever em silêncio. O erro explícito é a proteção do framework nesta versão. O grafo do sistema é sequencial, então a demonstração é de um grafo à parte e mostra por que cada campo acumulado tem reducer. A tabela de campos e a razão de cada reducer estão em `docs/arquitetura.md` §7.

## 6. Erros: recuperáveis e fatais

Limite de taxa, falha de conexão e timeout do modelo são recuperáveis: até 3 tentativas com espera de 2 e 4 segundos. Qualquer outro erro (chave inválida, requisição inválida) é fatal e vira `erro_fatal_llm`. Erro de ferramenta é dado: volta ao modelo como resultado com o campo `erro`. Ferramenta inexistente, argumento inválido e contrato sobrescrito pelo modelo também viram dado; o contrato vem da sessão e substitui o que o modelo digitar, registrado como `contrato_sobrescrito`.

## 7. Checkpoints

Cada atendimento tem `thread_id` no formato `contrato:uuid8`. Os checkpoints ficam em `dados/checkpoints.db` (SqliteSaver), e o estado pausado fica gravado no arquivo (a retomada a partir de outro processo é possível pelo framework, mas o terminal atual espera no mesmo processo; ver `docs/humano.md` §4). A remoção de um titular apaga os checkpoints do contrato.
