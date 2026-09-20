# Case — Agente de Suporte Técnico Doméstico

## 1. A indústria e o problema

**Setor:** empresas de internet e telefonia (provedores de internet).

**O problema em uma frase:** descobrir e resolver o motivo de a internet da
casa do cliente estar ruim ou fora do ar na hora, rodando testes automáticos
na linha, sem precisar passar por um atendente humano.

**Quem sofre com ele hoje:** o cliente residencial do provedor, no momento em
que a internet cai e ele precisa abrir um chamado — hoje pelo telefone ou
chat da central de atendimento.

### 2.1 O contexto

**O que acontece hoje:** o cliente fica sem internet e liga ou manda mensagem
para o suporte. Ele passa por um menu de botões ou por um atendente humano
que faz perguntas repetitivas ("o modem tá ligado?", "tirou da tomada?") por
14 a 20 minutos antes de resolver o problema ou encaminhar um técnico.

**Linha de base medida:** 14 min 20 s por chamado de suporte no canal
digital, medidos em 10 atendimentos reais no provedor parceiro (ver §2.5).

**Regras de domínio:**
- Prazos: resolver problemas simples em menos de 5 minutos pelo chat; se
  precisar de técnico, agendar para no máximo o dia seguinte.
- Quem pode fazer o quê: o agente só mexe em configuração do sistema
  (reiniciar o sinal, mudar a senha do Wi-Fi, reconectar a conta). Ações que
  custam dinheiro ou alteram o contrato (visita técnica, desconto na conta)
  exigem confirmação explícita do cliente ou aprovação de um funcionário
  humano.
- Segurança: para mexer na linha do cliente, o sistema precisa confirmar o
  número do contrato antes de agir.

**O que dá errado hoje (casos difíceis):**
- **Sintoma não bate com a causa real** — o cliente diz só "minha internet
  não funciona", mas a causa pode ser um cabo mal encaixado, a tomada
  desligada ou o sinal de fibra fraco vindo da rua.
- **Problema no bairro inteiro** — um rompimento de cabo na rua derruba a
  internet de centenas de casas ao mesmo tempo; o sistema precisa perceber
  que o caso é coletivo e não mandar um técnico por casa.
- **Internet "vai e volta"** — a rede cai por segundos e volta; um teste
  pontual não pega o problema, e o cliente segue insatisfeito mesmo com o
  teste "limpo".

## 2. Os usuários, e como será a interação

### 2.1 Perfis

| Perfil | O que ele quer | O que ele sabe | O que ele **pode** fazer |
|---|---|---|---|
| **Cliente residencial** (usuário principal) | ter a internet de volta sem perder tempo no telefone | só o que vê em casa ("a luz ficou vermelha", "a internet caiu") | descrever o problema, mexer em cabo/tomada, **aprovar** a visita do técnico |
| Técnico de suporte avançado | receber só os casos difíceis, já com os testes prontos | rede, sinais e cabos de fibra | trocar modem, dar desconto, mandar equipe de rua (fora do escopo desta entrega) |
| Gerente da operação | acompanhar quedas na cidade e não deixar clientes sem resposta | rede da cidade e metas de atendimento | marcar bairro em manutenção no sistema, pausando envio de técnico individual |

O **usuário principal** é o cliente residencial: quando os interesses
entram em conflito (§2.5), o sistema é desenhado a favor dele — priorizando
diagnóstico correto sobre custo de deslocamento.

### 2.2 Como é a interação

- **Canal:** WhatsApp, porque é onde o cliente já reclama hoje; não exige
  instalar nada nem aprender um app novo.
- **Quem começa:** o cliente (reativo). A entrada automática por queda de
  bairro é tratada à parte, sem abrir uma conversa individual por cliente.
- **Trocas até resolver:** 3 a 5 mensagens, na maioria dos casos.
- **O que o sistema devolve:** texto explicando o diagnóstico e o que foi
  feito; em caso de falha física, uma proposta de data para visita técnica.
- **Como termina:** com sucesso, confirma que o sinal voltou e pede para o
  cliente testar; sem sucesso, oferece agendar o técnico ou escala para um
  atendente humano.

**Diálogo de exemplo:**

Cliente: Boa noite, minha internet caiu e a luz do aparelho ficou vermelha. Agente: Olá! Vou testar a sua linha aqui no sistema agora mesmo, só um segundo... Agente: Vi aqui que o sinal de fibra que chega na sua casa está fraco. Não tem problema no seu bairro. Consegue ver se o cabinho amarelo atrás do modem está bem encaixado? Cliente: O cachorro encostou e o cabo tava solto! Encaixei de novo. Agente: Ótimo, vou reiniciar sua conexão daqui do sistema. Agente: Pronto! O sinal voltou ao normal e o aparelho já conectou. Pode testar a internet agora? Cliente: Voltou sim! Muito obrigado.

**A complexidade da interação:**
- **O que o cliente não informa de primeira:** a causa real do defeito — só
  descreve o que vê ("Wi-Fi sumiu", "tá lento"). O agente precisa investigar
  com testes automáticos.
- **Quando o relato contradiz o teste:** cliente diz "caiu tudo", mas o
  teste mostra `status: ONLINE` — o agente não fecha o caso nesse resultado;
  pede mais detalhes ou orienta um teste local (ver caso C002 em §2.8).
- **Quando o agente decide que já sabe o suficiente:** depois de rodar
  `testar_linha` e, se necessário, `conferir_queda_bairro`, com no máximo 3
  testes de linha por atendimento (limite de orçamento, não de política).
- **Quando chama um humano:** se o assunto for cobrança/fatura/cancelamento
  (nunca é tratado pelo agente técnico); se passarem 6 mensagens sem
  resolução; ou se o cliente pedir para falar com uma pessoa.

  ## 3. O workflow do agente
ENTRADA cliente escreve no WhatsApp [decide: CÓDIGO — roteamento do webhook]
SEPARAÇÃO é técnico, config, cobrança ou queda geral? [decide: MODELO — classificação de intenção]
DIAGNÓSTICO testar_linha / conferir_queda_bairro [decide: MODELO escolhe qual testar; CÓDIGO aplica limite de 3 testes]
AÇÃO reiniciar_conexao, se não houver falha física [decide: MODELO]
VERIFICAÇÃO roda testar_linha de novo antes de dizer "resolvido" [decide: CÓDIGO — checagem dupla fixa]
AGENDAMENTO se não resolveu, propõe visita; só agenda com "sim" do cliente [ESCRITA irreversível de custo — confirma com o cliente]
REGISTRO grava a trajetória e o resultado no log [decide: CÓDIGO]
RESPOSTA responde ao cliente em linguagem simples [decide: MODELO]

Dos 8 passos, 3 têm decisão do modelo (2, 3, 4 e 8) e o resto é código fixo —
a maior parte do sistema é, de fato, regra determinística; a parte que
justifica um agente está concentrada nos passos 2 a 4 (ver §2.5).

## 4. O sistema

**O que o sistema faz:** recebe a reclamação do cliente pelo WhatsApp, testa
a linha automaticamente, tenta resolver à distância (reinício, troca de
senha) e, se não conseguir, propõe e agenda uma visita técnica — sempre com
confirmação do cliente para qualquer ação que gere custo.

**Nível de autonomia: agente simples** (não workflow, não roteador puro). Um
workflow de árvore fixa falha no caso "sintoma não bate com a causa": o
cliente descreve o que vê em texto livre, e o próximo teste a rodar depende
do resultado do teste anterior — não existe uma ordem fixa de perguntas que
cubra "luz vermelha" + "sinal fraco" + "bairro sem queda" e ainda assim
levem à causa certa. Um roteador (uma única classificação e então uma
ferramenta fixa) também não basta, porque o número de testes e a decisão de
agendar dependem do **resultado intermediário**, não só da mensagem inicial.

**As ferramentas:**

| Ferramenta | O que faz | Leitura/escrita | Reversível? | Contra o que conversa |
|---|---|---|---|---|
| `obter_data_atual` | retorna a data de hoje e a de amanhã | leitura | — | relógio do sistema, não o provedor |
| `testar_linha` | lê status e sinal do modem | leitura | — | SQLite `provedor.db` |
| `conferir_queda_bairro` | verifica manutenção no bairro | leitura | — | SQLite `provedor.db` |
| `reiniciar_conexao` | reinicia a conexão à distância | escrita | sim | SQLite `provedor.db` |
| `agendar_visita_tecnico` | agenda visita, só com confirmação do cliente | escrita | não (desloca técnico) | SQLite `provedor.db` |

`obter_data_atual` é a quinta ferramenta, além das quatro do case original —
existe só porque o modelo não tem relógio e precisa saber que dia é hoje
para propor a data de uma visita técnica (regra do domínio §2.1). Ela não
envolve nenhuma decisão do agente (não lê nem escreve no sistema do
provedor), então não conta como parte da complexidade de diagnóstico do
sistema — é um utilitário.

## 5. A justificativa de negócio

**Por que agente, e não software comum:** a triagem exige interpretar
relatos informais e ambíguos ("luz piscando", "internet lenta") e decidir em
tempo real qual teste rodar com base no resultado do teste anterior. Um
formulário de regras fixas trava quando o cliente descreve o sintoma de um
jeito inesperado ou quando o teste retorna um resultado fora do padrão
previsto — por isso o nível "workflow" não dá conta (ver §4).

**O ganho esperado:**

| Eixo | Linha de base (medida) | Alvo | Ganho | Volume |
|---|---|---|---|---|
| Tempo por tarefa | 14 min 20 s por chamado (10 atendimentos reais medidos no provedor parceiro) | 3 min 45 s por chamado resolvido pelo agente | −10 min 35 s por atendimento | 180 chamados/dia |
| Cobertura sem humano | 0% dos chamados de triagem resolvidos sem atendente | 65% dos chamados de rotina resolvidos sem transbordo | +65 p.p. | 5.400 chamados/mês |

Ambos os números vêm do case original; são uma **estimativa de alvo** a
partir de uma linha de base medida, não um resultado já observado.

**Ganho do usuário vs. ganho do negócio:**
- Para o cliente: resolução imediata, sem menu de botões e sem repetir o
  problema para vários atendentes.
- Para o negócio: menos custo por chamado e menos deslocamento de técnico
  para problemas simples de cabo ou tomada.
- **A tensão:** para o negócio, o ideal é nunca despachar um técnico; para o
  cliente, se o sinal não volta, a prioridade é a visita mais rápida
  possível. O agente resolve essa tensão a favor do diagnóstico correto: se
  o teste confirmar falha física (sinal óptico ≤ −27dBm), ele já propõe o
  agendamento em vez de insistir em testes que não vão resolver.

**O outro lado da conta:**
- **Custo de rodar:** ver `docs/modelos.md` §2 — a estimativa por execução e
  por mês.
- **Custo de construir:** esforço do grupo nesta entrega (poucas horas por
  pessoa, escopo deliberadamente pequeno).
- **O que se perde:** o caso de rede "vai e volta" (§2.1) — se o teste for
  pontual, o agente pode dizer "resolvido" com o cliente ainda insatisfeito;
  quem paga por isso é o cliente, que liga de novo.

## 6. O verificador

Conjunto de **casos rotulados à mão**: para cada caso de teste (os 4 de
§2.8 mais outros que o grupo adicionar), definimos manualmente qual é a
ação correta esperada do agente (reiniciar / agendar visita / escalar para
humano / não agir). O verificador compara a ação realmente tomada pelo
agente (lida do log de trajetória) com a ação esperada da tabela.

## 7. O critério de sucesso

O agente acerta a ação correta (reiniciar, agendar, escalar ou não agir) em
pelo menos **8 de 10** casos rotulados à mão, **e** não agenda nenhuma
visita individual em caso de bairro em manutenção (erro assimétrico: um
agendamento indevido custa deslocamento real, então essa condição não abre
exceção mesmo que a taxa geral esteja ok).

## 8. Dados

Simulados: um banco SQLite (`dados/provedor.db`), gerado por um script de
seed (`src/db.py`), com clientes, modems e bairros fictícios. Casos difíceis
nomeados:
- **Divergência:** cliente C002 — o teste mostra `ONLINE`, mas a mensagem do
  cliente diz que a internet caiu.
- **Registro inexistente:** contrato `C999`, que não existe na base.
- **Não deve disparar a ação principal:** cliente C005, cujo bairro
  (Jardim Ipê) está marcado como em manutenção — o agente não deve agendar
  visita individual para ele.

## 9. Dado sensível

O tema toca dado pessoal: nome, bairro e número de contrato do cliente.
Nenhum dado real de cliente entra no repositório nem no prompt — a base é
inteiramente sintética (§2.8), e o número de contrato usado nos testes é
fictício.

## 10. Espaço para o que vem

- [x] **RAG** (Parte 2): o manual de causas comuns de sinal fraco/perda de
  fibra do provedor, hoje só existe como PDF interno não estruturado.
- [x] **MCP** (Parte 2): a camada de acesso ao "sistema do provedor"
  (`testar_linha`, `conferir_queda_bairro`, `reiniciar_conexao`,
  `agendar_visita_tecnico`) vira servidor MCP.
- [ ] **LangChain** (Parte 2): ainda não decidido em que parte da
  orquestração ela entraria.
- [x] **Multiagente** (Parte 3): o agente de apoio ao técnico de campo,
  detalhado no PDF da parte 2 da entrega original (recebe fotos do conector
  óptico, mede sinal na caixa da rua, provisiona modem novo). Por que mais
  de um agente: os dois perfis têm ferramentas e nível de conhecimento
  completamente diferentes (cliente leigo vs. técnico especialista), e o
  handoff entre eles — do diagnóstico remoto ao reparo em campo — é o que
  fecha o ciclo do atendimento.

## 11. O maior risco

O caso de rede "vai e volta" (§2.1): se o teste automático capturar a linha
num instante em que ela está temporariamente normal, o agente conclui
"resolvido" com o problema real ainda presente. Plano B: antes de fechar o
atendimento como resolvido, rodar `testar_linha` uma segunda vez após um
intervalo (em vez de uma checagem única), e perguntar diretamente ao
cliente se o problema persiste depois de alguns minutos.