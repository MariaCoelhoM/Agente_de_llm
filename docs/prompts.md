# Plano de prompt engineering

Os prompts vivem em `src/prompts/` e são lidos em tempo de execução. Este documento explica as escolhas; os arquivos são a fonte.

## 1. As etapas e onde o modelo é chamado

O modelo é chamado em um lugar só: o nó `agente`, uma vez por volta. As outras etapas que poderiam usar o modelo são código, e a tabela diz por quê.

| Etapa | Modelo? | Técnica | Por que ela | Contrato de saída | Como é testada |
|---|---|---|---|---|---|
| agente (cada volta) | sim | zero-shot com regras explícitas e chamada de função; memória procedural (4 regras) e bloco de memória no contexto | o formato é imposto pelo esquema das ferramentas, as regras do domínio cabem em frases curtas, e exemplos de diálogo custariam tokens em toda volta. Não foi comparada uma variante few-shot; zero-shot bastou nas execuções reais | ver §1.1 | 57 testes com modelo simulado (comportamento do sistema diante de cada saída) e 10 execuções reais em `docs/io.md` (obediência do modelo) |
| triagem | não | regex sobre texto sem acento | as rotas são poucas e se reconhecem por palavra; custo zero e determinística | rota `humano`, `incompleta` ou `suporte` | `tests/test_grafo.py`: cobrança vai para humano sem chamar o modelo; três mensagens sem sintoma pedem detalhes sem chamar o modelo |
| extração de fato para a memória | não | regra sobre o que as ferramentas devolveram (`memoria.extrair_episodio`) | deixar o modelo decidir o que lembrar guarda demais e guarda errado (`docs/memoria.md` §3) | um episódio e, se houve teste de linha, o último sinal | `tests/test_memoria.py`: só entra o que a ferramenta devolveu |
| resposta com manual | não é etapa à parte | o modelo consulta o corpus como ferramenta e responde na volta seguinte | a recuperação é decisão do modelo (`docs/rag.md` §6) | a mesma do agente, com citação de id | validação em código no nó `finalizar` |
| validação da saída | não | modelo Pydantic `RespostaAtendimento` | a verificação de fonte e citação é verificável por regra | ver `docs/arquitetura.md` §9 | `tests/test_grafo.py` (citação inválida, recusa por portão, saída inválida) |

### 1.1 O contrato do agente, exato

O modelo produz dois tipos de saída:

**Pedido de ferramenta.** O nome é um dos seis oferecidos (`obter_data_atual`, `testar_linha`, `conferir_queda_bairro`, `reiniciar_conexao`, `propor_visita`, `consultar_base_conhecimento`) e os argumentos seguem o esquema de cada uma. O contrato nunca é argumento do modelo: o grafo injeta o da sessão e registra `contrato_sobrescrito` se o modelo tiver escrito outro.

**Texto final.** Português, frases curtas. Ids de trecho do manual entre colchetes, como `[S01]`, e só os que a ferramenta devolveu naquela execução.

**Proibido aparecer** (cada item tem a regra no prompt e a proteção em código):

| Proibido | Proteção em código |
|---|---|
| agendar, ou dizer que agendou, antes do resultado da proposta | o modelo não tem a ferramenta que agenda; só o nó `agendar` escreve |
| perguntar ou digitar o contrato | o contrato da sessão substitui o do modelo |
| tratar cobrança, fatura, desconto ou cancelamento | a triagem desvia para humano antes do modelo |
| propor visita individual com o bairro em manutenção | `propor_visita` recusa |
| citar um id que a ferramenta não devolveu | `finalizar` separa em `citacoes_invalidas` e não conta como fonte |
| apresentar a memória do sistema como fala do cliente | o bloco vem marcado como "não confirmado pelo cliente agora" |
| dizer que resolveu sem novo teste depois de reiniciar | só no prompt; ver §3 |

O objeto `RespostaAtendimento` não é escrito pelo modelo: o código o monta a partir do texto e da trajetória.

## 2. Os prompts em arquivo e as versões

| Arquivo | Papel | Versão em uso nos logs de 19/10/2026 (sha256, 12 primeiros) |
|---|---|---|
| `src/prompts/suporte_v2.md` | prompt do agente | `8ff597289d95` |
| `src/prompts/procedural.md` | memória procedural, entra no prompt de toda execução | `5ecc9d266e5f` |
| `prompts/suporte_v1.md` | prompt da Parte 1, mantido como histórico | não usado |

Cada log registra, no campo `prompts`, o arquivo e o hash do conteúdo em uso. Mudar `procedural.md` muda o comportamento do agente, então a mudança passa por revisão como qualquer código.

Mudanças da v1 para a v2:

| Mudança | Motivo |
|---|---|
| o modelo usa `propor_visita`, não agenda | a confirmação passou a ser estrutural; o texto não precisa mais pedir "só agende com sim" |
| citar o id do trecho entre colchetes | a saída é validada contra os trechos realmente recuperados |
| se a ferramenta disser `suficiente=false`, recusar e oferecer humano | o portão do RAG existe, e o prompt diz como se comportar diante dele |
| contrato da sessão informado | o modelo não o pergunta nem o digita |
| histórico do cliente é contexto, não afirmação | a memória não vira fato sem confirmação por ferramenta |
| informar o resultado exato da proposta | o modelo só fala de agendamento depois que o nó `agendar` devolve o resultado |
| mensagem sem sintoma: perguntar antes de testar; relato com duas leituras: escolher uma e declarar | cobrem os casos 1.4 do enunciado (§3.2 e §3.3 abaixo) |

## 3. A regra da frase

### 3.1 Frase removida: o reteste depois do reinício

`python -m scripts.experimento_frase 5` remove do prompt a frase "Nunca diga que resolveu sem rodar testar_linha de novo depois de reiniciar_conexao" e roda o mesmo caso (C001, "A luz do modem está piscando vermelha e a internet caiu.") cinco vezes com e cinco sem a frase, com o modelo real e bancos temporários. A métrica vem da trajetória: depois de `reiniciar_conexao`, houve `testar_linha` antes da resposta?

| Variante | Execuções em que reiniciou | Rodou `testar_linha` depois |
|---|---|---|
| com a frase | 4 de 5 | 4 |
| sem a frase | 4 de 5 | 4 |

Sem a frase, o comportamento não mudou. O resultado vale para este modelo, este caso e N=5; não prova que a frase é inútil em outros casos. A frase **voltou** e foi mantida, por duas razões: custa uma linha, e o erro que ela evita (dizer "resolvido" sem reteste) é caro e o código não o verifica. A frase repete uma regra que também está na memória procedural e no corpus (S12), o que explica por que tirar uma das três cópias não muda nada. O experimento completo está em `docs/experimento_frase.md`.

### 3.2 Frase que não impedia nada: "não use ferramentas ainda"

A v2 tinha a instrução de perguntar o que falta, sem usar ferramentas, quando a mensagem não diz qual é o problema. Com a entrada "não funciona", o modelo chamou `testar_linha` e `conferir_queda_bairro` mesmo assim, e a resposta saiu com `suficiente=true`. A frase não impedia o que dizia impedir. A regra foi para o código: a triagem detecta mensagem sem nenhuma palavra de sintoma e devolve um pedido fixo de detalhes sem chamar o modelo (`caso_entrada_incompleta`: zero ferramentas, zero tokens, `suficiente=false`). A frase continua no prompt para mensagens vagas que contenham uma palavra de sintoma, e ela é a próxima candidata ao mesmo experimento.

### 3.3 Entrada ambígua: o que se viu

Com "A internet está ruim hoje, não sei se é o wifi ou a internet mesmo", a regra "escolha a leitura mais provável e diga qual" foi seguida na execução de 19/10 ("o problema provavelmente é no wifi, não na internet"). Em outra execução do mesmo caso, o modelo escreveu "faz os dois testes que te pedi", sem ter pedido nada antes. Foi uma ocorrência, e não houve proteção em código para isso.

## 4. A triagem

A triagem é regra de código: palavras de cobrança, fatura, desconto, segunda via, cancelamento, pagamento, reembolso e pedido de atendente vão para humano; mensagem sem nenhuma palavra de sintoma recebe um pedido de detalhes. É determinística, custa zero e é testável.

Limites: um pedido de cobrança sem nenhuma dessas palavras chega ao agente, e o prompt e a política P02 o desviam para humano; uma mensagem vaga que contenha uma palavra de sintoma ("a internet") também chega ao agente.
