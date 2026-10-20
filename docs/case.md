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

Atualizado na Parte 2 para o que o sistema faz hoje (o desenho está em `docs/arquitetura.md`).

| Passo | O que acontece | Quem decide |
|---|---|---|
| 1. ENTRADA | o cliente escreve no WhatsApp; o contrato vem da sessão | CÓDIGO |
| 2. SEPARAÇÃO | cobrança, cancelamento ou pedido de atendente vão para humano; mensagem sem sintoma recebe um pedido de detalhes | CÓDIGO (regras de palavra, sem chamar o modelo) |
| 3. DIAGNÓSTICO | `testar_linha`, `conferir_queda_bairro`, `consultar_base_conhecimento` | MODELO escolhe qual; CÓDIGO aplica o limite de 3 testes e detecta laço |
| 4. AÇÃO | `reiniciar_conexao`, se não houver falha física | MODELO escolhe; CÓDIGO recusa se o sinal é igual ou pior que -27 dBm |
| 5. VERIFICAÇÃO | roda `testar_linha` de novo antes de dizer "resolvido" | MODELO, por instrução do prompt; não há trava em código (medido em `docs/experimento_frase.md`) |
| 6. AGENDAMENTO | `propor_visita` valida; o grafo pausa; o cliente aprova, rejeita ou edita a data; só então o código agenda | CÓDIGO e CLIENTE; o modelo não tem a ferramenta que agenda |
| 7. REGISTRO | grava a trajetória no log e a memória do atendimento | CÓDIGO |
| 8. RESPOSTA | responde ao cliente em linguagem simples; o código valida fontes e contrato de saída | MODELO escreve; CÓDIGO valida |

Dos 8 passos, 4 têm decisão do modelo (3, 4, 5 e 8) e o resto é código fixo. A maior parte do sistema é regra determinística; a parte que justifica um agente está concentrada nos passos 3 a 5 (ver §4).

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
| `propor_visita` | valida a data (hoje até amanhã), o contrato e o bairro; não escreve nada | validação | — | SQLite `provedor.db` |
| `consultar_base_conhecimento` | busca trechos nos manuais e políticas; recusa quando nada cobre a pergunta | leitura | — | corpus em `dados/corpus` |
| `agendar_visita_tecnico` | agenda visita; o modelo não a chama, quem chama é o código depois da aprovação do cliente | escrita | não (desloca técnico) | SQLite `provedor.db` |

`obter_data_atual` existe só porque o modelo não tem relógio e precisa saber
que dia é hoje para propor a data de uma visita técnica (regra do domínio
§2.1). Ela não lê nem escreve no sistema do provedor, então não conta como
parte da complexidade de diagnóstico: é um utilitário. A Parte 2 acrescentou
`propor_visita` e `consultar_base_conhecimento` às quatro ferramentas do case
original.

A defesa do nível de autonomia, feita com o sistema rodando, está em
`docs/arquitetura.md` §5.

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
- [ ] **MCP** (Parte 2): a camada de acesso ao "sistema do provedor"
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

## 12. O que o domínio ensinou (complemento da Parte 2)

Esta seção registra o que ficou claro ao construir o sistema sobre este domínio e que não está nas seções anteriores. Cada item aponta para onde aparece no projeto.

### 12.1 O vocabulário

| Termo | O que significa aqui |
|---|---|
| ONT / modem óptico | o aparelho que recebe a fibra na casa do cliente. É separado do roteador Wi-Fi (`dados/corpus/03_equipamentos_limiares.md`, E06) |
| dBm | a medida do sinal óptico. Quanto mais negativo, pior: -22 é normal, -30 é falha |
| zona cinzenta | sinal entre -25 e -27 dBm: funciona, mas é instável (E02, S08) |
| falha física | sinal igual ou pior que -27 dBm: cabo, conector ou fibra com problema. Reinício remoto não resolve (E03, S07) |
| ONLINE / OFFLINE | o que o teste de linha devolve. ONLINE com sinal normal significa que a fibra está boa e o problema está dentro da casa (E05) |
| bairro em manutenção | queda coletiva: a equipe de rede já está atuando e nenhuma visita individual se justifica (S09) |
| reinício remoto | reinicia a conexão pelo sistema do provedor. Não é o mesmo que o cliente reiniciar o roteador dele |

### 12.2 Regras que todo mundo da área conhece e nenhum documento registrava

- A **luz vermelha piscando** e a **luz vermelha fixa** não são o mesmo defeito. Piscando é perda de sinal óptico (cabo, fibra); fixa é falha de energia ou do equipamento (S01, S02, E01). Quem trata as duas igual manda o técnico errado.
- **Reiniciar não é sempre inofensivo.** Cada reinício conta no contador diário do modem, e com falha física ele não adianta (E04). Por isso a ferramenta recusa o reinício quando o sinal é igual ou pior que -27 dBm.
- **"Resolvido" só vale depois de um novo teste** que confirme ONLINE com sinal normal (S12). O reinício sozinho não prova nada.
- **Problema só de Wi-Fi não aparece no teste de linha.** O teste olha a fibra; o roteador do cliente é outra peça (E06, S04).
- Quem decide a visita é o cliente, e a data pode ser mais longe do que o agente propõe: o agente propõe até o dia seguinte, o cliente pode escolher até 14 dias (P04).

### 12.3 O passo que parecia um e são três

"Agendar a visita técnica" parecia um passo. São três, com donos diferentes:

1. **Propor**: `propor_visita` valida data, contrato e bairro, e não escreve nada. É a única porta do modelo.
2. **Decidir**: o grafo pausa e o cliente aprova, rejeita ou edita a data. Se ele não responde no prazo, nada é agendado.
3. **Gravar**: o código agenda, e repetir a mesma aprovação não cria uma segunda visita.

Na Parte 1 esse passo era uma varredura da palavra "sim" na conversa. Separá-lo em três foi o que permitiu tirar do modelo a ferramenta que gera custo.

### 12.4 As exceções que decidiram a arquitetura

- **O cliente reclama e o teste da linha está normal.** Em `caso_C002_divergencia` e `caso_C005_nao_agenda` o sinal é bom (-18 e -19 dBm), mas o bairro está em manutenção. Mesmo quando o cliente pede um técnico ("quero que mandem um técnico hoje"), nenhuma visita individual é agendada. Essa regra está no código (`propor_visita`), não só no prompt.
- **Contrato inexistente.** Em `caso_C999_inexistente` nenhuma ferramenta consegue testar a linha. A resposta sai com `suficiente=false` e oferece um atendente humano, em vez de inventar um diagnóstico.
- **Manual desatualizado.** O corpus mantém `04_manual_sintomas_v0`, revogado, que contradiz os documentos atuais em três números. Deixá-lo no índice faria o sistema citar valor errado com aparência de fonte (`docs/rag.md`).
- **Mensagem sem sintoma.** "não funciona" não diz o que testar. Quando essa regra ficou só no prompt, o modelo testou a linha mesmo assim; hoje ela é uma regra de triagem em código (`caso_entrada_incompleta`).
- **O caso "vai e volta"** (§2.1 e §11) continua sendo a exceção sem solução completa: a zona cinzenta pede dois testes com intervalo (S08), e o limite de 3 testes por atendimento convive com isso.

### 12.5 O que este case não sabe

Os manuais e as políticas do corpus são simulados: foram escritos pelo grupo a partir do domínio do case, e os limiares (por exemplo -27 dBm) são valores do projeto, não de um fabricante ou de uma operadora real. A linha de base de 14 min 20 s vem de 10 atendimentos medidos no provedor parceiro (§2.1) e não foi remedida na Parte 2.
