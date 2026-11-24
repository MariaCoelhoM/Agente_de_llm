<!-- Transcrição fiel do PDF "Agente de Suporte Técnico Doméstico.pdf" (material do grupo, Parte 1). O PDF foi removido do repositório; o conteúdo está aqui. -->

# Agente de Suporte Técnico Doméstico

## 1. O case — indústria e problema

**O setor:** Empresas de Internet e Telefonia (Provedores de Internet).

**O problema, em uma frase:** Descobrir e resolver o motivo de a internet da casa do cliente estar ruim ou fora do ar na hora, rodando testes automáticos na linha sem precisar passar por um atendente humano.

**O contexto de onde o problema vive:**

- **O que acontece hoje:** O cliente fica sem internet e manda mensagem ou liga. Hoje ele passa por menus chatos de apertar botões ou fala com um atendente que faz perguntas repetitivas ("o modem tá ligado?", "tirou da tomada?") por 15 a 20 minutos antes de tentar resolver ou mandar um técnico na casa dele.
- **As regras domínio:**
  - **Prazos:** Resolver problemas simples em menos de 5 minutos pelo chat; se precisar mandar técnico em casa, agendar para no máximo o dia seguinte.
  - **Quem pode fazer o quê:** O robô só pode mexer nas configurações do sistema (reiniciar o sinal da rua, mudar a senha do Wi-Fi, reconectar a conta). Coisas que custam dinheiro ou alteram o contrato (marcar visita de técnico na casa do cliente ou dar desconto na conta) precisam da aprovação do próprio cliente ou de um funcionário humano.
  - **Segurança:** Para mexer na linha do cliente ou reiniciar o aparelho de longe, o sistema precisa conferir com certeza os dados do dono do contrato.
- **O que dá errado hoje (os casos difíceis):**
  - **Falar o sintoma, mas a causa ser outra:** O cliente diz apenas "minha internet não funciona", mas o motivo real pode ser um cabo amarelo mal encaixado atrás do modem, a tomada desligada ou o sinal da fibra que vem da rua que está fraco.
  - **Problema no bairro inteiro:** Um caminhão passa e arrebenta um cabo na avenida, deixando 200 casas sem internet ao mesmo tempo. Em vez de mandar um técnico para a casa de cada cliente, o sistema precisa perceber que o problema é geral e avisar a equipe de rua para arrumar o cabo principal.
  - **Internet "vai e volta":** A rede cai por alguns segundos e volta. Quando o sistema testa de relance parece tudo certo, mas o cliente continua com o serviço ruim.

**O que as grandes empresas já fazem:**

- **Comcast (EUA):** Usa um assistente no aplicativo que roda testes no modem sozinho enquanto conversa com o cliente. **O que não contam:** Se a fibra arrebentar fisicamente ou o aparelho quebrar de vez, o robô não consegue diagnosticar sozinho e ainda precisa mandar para um atendente humano.
- **Vodafone (Europa):** Usa um robô de atendimento para responder às primeiras dúvidas técnicas no chat. **O que não contam:** Omitiram a quantidade de clientes que ficaram insatisfeitos com respostas genéricas e precisaram ligar de novo no dia seguinte.

## 2. Os usuários, e como será a interação

**Tabela de perfis:**

| Perfil | O que ele quer | O que ele sabe | O que ele pode fazer |
|---|---|---|---|
| Cliente (Usuário Principal) | Ter a internet funcionando de novo sem perder tempo no telefone. | Só vê o que está acontecendo na casa dele ("a luz do modem ficou vermelha", "a TV travou"). | Contar o problema, apertar ou encaixar cabos em casa e aprovar a visita do técnico. |
| Técnico do Suporte Avançado | Receber só os casos difíceis, já com os testes prontos. | Entende tudo de redes, sinais e cabos de fibra. | Mandar trocar o modem, dar descontos e enviar a equipe de rua para consertos. |
| Gerente da Operação | Acompanhar quedas na cidade inteira e não deixar os clientes sem resposta. | Sabe como funciona a rede da cidade e as metas de atendimento da empresa. | Avisar no sistema que o bairro está em manutenção para pausar o envio de técnicos individuais. |

**O usuário principal:** O Cliente em Casa. Quando o cliente estiver ansioso querendo uma resposta rápida, o sistema explica o que está fazendo enquanto roda os testes no fundo.

**A interação, na prática:** Acontece pelo WhatsApp. O cliente manda mensagem dizendo que está sem internet. O robô pega o número do contrato e já testa o modem dele no sistema da empresa antes mesmo de dar a primeira resposta. Tudo se resolve em 3 a 5 mensagens. Se for um defeito físico que não dá para arrumar pela conversa, o robô oferece os horários disponíveis e marca a visita do técnico com a autorização do cliente.

**Conversa de exemplo:**

> **Cliente:** "Boa noite, minha internet caiu e a luz do aparelho ficou vermelha."
>
> **Agente:** "Olá! Vou testar a sua linha aqui no sistema agora mesmo, só um segundo..." (Sisteminha roda o teste automático)
>
> **Agente:** "Vi aqui que o sinal de fibra que chega na sua casa está muito fraco. Não tem nenhum problema no seu bairro. Consegue dar uma olhada se o cabinho amarelo atrás do modem está bem encaixado?"
>
> **Cliente:** "Dê uma olhada aqui, o cachorro encostou e o cabo tava meio solto! Encaixei de novo."
>
> **Agente:** "Ótimo! Vou reiniciar a sua conexão daqui do sistema agora." (Envia o comando de reinício)
>
> **Agente:** "Pronto! O sinal voltou ao normal e seu aparelho já conectou. Pode tentar usar a internet agora?"
>
> **Cliente:** "Voltou sim! Muito obrigado."

**O que o cliente não conta de primeira:** O motivo real do defeito. Ele só consegue dizer o que está vendo ("o Wi-Fi sumiu", "tá lento"). Cabe ao robô investigar por conta própria, usando os testes automáticos da empresa, se a falha é na tomada dele, no cabo, na configuração do sistema ou no bairro inteiro.

## 3. Os ganhos esperados

**Por que um agente, e não software comum:** O diagnóstico exige interpretar relatos informais e ambíguos do cliente ("luz piscando", "rede caindo") e decidir, em tempo real, qual ferramenta de teste acionar no sistema do provedor com base nos dados que retornam. Um formulário com regras fixas trava quando o cliente descreve o sintoma de forma inesperada ou quando o teste de rede retorna um erro fora do padrão esperado.

**Eixos de ganho:**

| Eixo | Linha de base (medida) | Alvo | Ganho | Volume |
|---|---|---|---|---|
| Tempo por tarefa | 14 min e 20 seg por chamado de suporte no canal digital (medido em 10 atendimentos reais no provedor parceiro). | 3 min e 45 seg por chamado resolvido pelo agente. | Economia de 10 min e 35 seg por atendimento. | 180 chamados/dia na unidade parceira. |
| Cobertura (% sem humano) | 0% dos chamados de triagem técnica resolvidos sem atendente humano. | 65% dos chamados de rotina resolvidos sem transbordo para o suporte. | Aumento de +65 p.p. na resolução automática no canal inicial. | 5.400 chamados/mês. |

**Ganho do usuário vs. Ganho do negócio (e a tensão entre eles):**

- **Para o cliente:** Ganho de tempo e usabilidade — resolução imediata do problema sem precisar esperar na fila do chat, passar por menus de botões engessados ou entender termos técnicos.
- **Para o negócio:** Redução do custo operacional de atendimento por chamada e menor necessidade de enviar técnicos de campo para resolver problemas simples de tomada ou cabo solto.
- **A tensão:** Para o negócio, o ideal é nunca enviar um técnico de rua, pois o deslocamento tem custo alto. Para o cliente, se o sinal não voltar rápido, a prioridade é ter a visita agendada o quanto antes. O agente é programado para resolver essa tensão em favor do diagnóstico correto: se os testes do sistema confirmarem falha física na fibra (sinal óptico zerado), o agente sugere imediatamente o agendamento de visita sem prender o cliente em testes inúteis.

**Checagem contra os 4 anti-padrões:**

- **Como saber se deu certo (Verificador):** É fácil de conferir no sistema. Depois de tentar arrumar, o agente roda o teste do modem de novo. Se o sinal estiver forte e o status mostrar "ONLINE", a resposta deu certo.
- **Acesso aos dados:** Vamos usar um sistema simulado, dados criados por nós para o trabalho com clientes e modems de teste, sem precisar pedir autorização para mexer na rede de uma empresa real.
- **Tamanho do projeto:** O foco é bem claro e cabe em uma frase, usando poucas ferramentas específicas (testar sinal, reiniciar conexão, checar queda no bairro e agendar visita).
- **Foco na arquitetura:** O valor central do projeto está na orquestração dos agentes de diagnóstico, uso de ferramentas e tomada de decisão.
