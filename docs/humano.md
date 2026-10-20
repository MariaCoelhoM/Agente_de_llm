# Humano no laço: aprovação da visita técnica

## 1. Onde o grafo para, e por qual critério

O grafo tem **um ponto de parada**: o nó `aprovacao`, marcado com `##` no diagrama de `docs/arquitetura.md` §2.

| Critério | Vale aqui? | Como |
|---|---|---|
| ação irreversível | sim | a visita técnica desloca um técnico e não se desfaz sozinha |
| custo acima de um teto | sim | toda visita tem custo de deslocamento; o case (§2.1) exige confirmação explícita para qualquer ação que gere custo |
| confiança baixa | não pausa | quando o RAG recupera pouco, o portão recusa e oferece um atendente; a execução termina, não espera |

A ação mais perigosa do sistema é agendar a visita. O `reiniciar_conexao` é escrita reversível e não pausa.

A pausa é estrutural: o modelo não tem a ferramenta que agenda. Ele tem `propor_visita`, que só valida (data entre hoje e amanhã, contrato existente, bairro fora de manutenção, um teste de linha anterior que justifique a visita, isto é, falha física provável ou linha OFFLINE, e cliente que ainda não recusou). Quem agenda é o nó `agendar`, depois do nó `aprovacao`.

**Quem é chamado.** O próprio cliente: quem sabe se a data serve e quem arca com a visita. Não é um atendente da operação.

## 2. O que a pessoa vê

O `interrupt` entrega a ação exata, e não um resumo do modelo: a ação (`agendar_visita_tecnico`), o contrato, a data proposta, a consequência ("desloca um técnico até a casa do cliente; tem custo e não é desfeito sozinho"), as opções (aprovar, rejeitar, editar), a janela de edição (de hoje até 14 dias) e o prazo. No terminal:

```
=== APROVAÇÃO NECESSÁRIA ===
Ação: agendar_visita_tecnico  contrato=C004  data=2026-10-20
Consequência: desloca um técnico até a casa do cliente; tem custo e não é desfeito sozinho
Prazo: 900s. Opções: aprovar | rejeitar | editar AAAA-MM-DD
```

## 3. As quatro saídas

| Resposta | O que o código faz |
|---|---|
| aprovar | agenda na data proposta |
| rejeitar | não agenda; o modelo informa o cliente e não insiste (propor de novo é recusado com `cliente_ja_recusou_a_visita`) |
| editar com data | valida a data (entre hoje e hoje + 14 dias); válida, agenda nela; inválida, vira rejeitar com motivo `edicao_invalida` |
| expirou | não agenda e encaminha para humano com o motivo `aprovacao_expirada` |

Qualquer resposta fora dessas quatro vira rejeitar. A edição existe porque a política P04 permite ao cliente escolher uma data posterior à proposta, e é o que separa aprovação de carimbo: o agente propõe até amanhã e o cliente pode corrigir a data antes de deixar seguir.

Exemplo real, `caso_C004_pausa_edita` (log de 19/10/2026): o grafo propôs 2026-10-20, a resposta foi `editar` com 2026-10-22, o código validou a data e agendou nela. O modelo disse ao cliente "A visita técnica foi agendada para 22/10/2026" só depois do resultado do nó `agendar`.

## 4. A implementação, e por que ela depende do checkpoint

A pausa é um `interrupt` dentro do nó `aprovacao` (`src/grafo.py:224`). A retomada é uma nova invocação com `Command(resume=...)` (`src/agent.py:109`), e o valor devolvido vira o retorno do `interrupt`. A retomada não continua da linha seguinte: o nó roda de novo desde o começo. Por isso o nó só lê o estado antes do `interrupt`, e nenhum efeito colateral acontece antes dele; o agendamento fica no nó seguinte.

Isso só funciona porque existe um checkpointer. A pausa é um checkpoint gravado, endereçado por `thread_id`, e o checkpointer é o `SqliteSaver` em `dados/checkpoints.db`. Os testes usam `InMemorySaver`, onde a aprovação pendente morreria com o processo.

Limite do que está implementado: o estado pausado fica gravado no arquivo, mas o terminal atual espera a resposta **no mesmo processo** (`decisor_terminal`). Retomar a partir de outro processo é possível pelo framework (reabrir o `thread_id` com `Command(resume=...)`), mas o programa não expõe isso.

## 5. O prazo, e o que acontece se ninguém responder

O terminal espera a resposta por `config.PRAZO_APROVACAO_SEGUNDOS` (900 s). Passado o prazo, a execução retoma com `expirou`: nada é agendado, o motivo de término é `aprovacao_expirada` e o cliente recebe o texto "Não recebi sua resposta sobre a visita técnica a tempo, então nada foi agendado. Vou encaminhar você para um atendente humano." O caminho está escrito e não segue adiante em silêncio. O tempo de espera não conta no teto de tempo do atendimento (`segundos_ativos` mede só tempo de máquina). `tests/test_grafo.py` cobre o caso (`test_expirar_nao_agenda_e_encaminha_humano`).

Limite: o prazo só vale enquanto o processo que espera está vivo. Se o processo cair, a execução fica pausada no checkpoint sem ninguém para retomá-la com `expirou`. Em produção, isso pediria um processo que varresse as pausas vencidas.

## 6. Aprovar duas vezes

O agendamento é idempotente: a chave deriva de contrato e data (`sha256(contrato|data)`), há índice único no banco, e a segunda aprovação devolve `ja_existia=True` sem criar outra linha.

**Prova com log.** `caso_C004_pausa_edita` e `caso_C004_aprovacao_repetida` são duas execuções reais, com `thread_id` diferentes, do mesmo contrato, em que a pessoa aprovou editando a mesma data. O resultado do agendamento, lido de `docs/io.md`:

| Execução | `thread_id` | Resultado do nó `agendar` |
|---|---|---|
| primeira | `C004:3c17344b` | `{"contrato": "C004", "data": "2026-10-22", "status": "AGENDADA", "ja_existia": false}` |
| segunda | `C004:23eb916f` | `{"contrato": "C004", "data": "2026-10-22", "status": "AGENDADA", "ja_existia": true}` |

A segunda chamada reconheceu a visita pela chave e não criou nada. O `gerar_io` só escreve a prova se a primeira execução devolveu `ja_existia=false`; caso contrário avisa que o banco precisa ser zerado (`python -m scripts.rodar_casos --reset C004 C004B`).

Também sem modelo, `python -m scripts.demo_idempotencia` mostra o mesmo no nível da ferramenta:

```
aprovação 1: {'contrato': 'C004', 'data': '2026-10-20', 'status': 'AGENDADA', 'ja_existia': False}
aprovação 2: {'contrato': 'C004', 'data': '2026-10-20', 'status': 'AGENDADA', 'ja_existia': True}
linhas em visitas: 1
```

`tests/test_grafo.py` repete o caso passando pelo grafo inteiro.

## 7. Como demonstrar

`python -m src.agent C004 "Sem internet nenhuma, a luz está vermelha."` pergunta no terminal. Para scripts: `--decisao aprovar`, `--decisao rejeitar`, `--decisao editar --data AAAA-MM-DD` e `--decisao expirou`.
