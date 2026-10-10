Markdown · aula-11-avaliacao.md

# aula-11-avaliacao.md

Avaliação do agente — Agente de Suporte Técnico Doméstico

Rascunho de exercicios/aula-11-avaliacao.md, no domínio de docs/case.md. O agente já mudou de modelo três vezes e de prompt quatro vezes desde a Entrega 1 (Mistral Small, depois Llama 3.1 8B, depois gpt-oss-20b, depois qwen/qwen3.8-27b; e o SYSTEM_PROMPT ganhou a regra do bairro em manutenção e a ferramenta obter_data_atual depois de bugs encontrados rodando os casos à mão). Cada troca foi validada olhando o log de uma execução, nunca contra as anteriores. Este documento desenha a suíte que fecha essa lacuna.

1. Os casos — o golden dataset v1

Os embriões reaproveitados: os 5 casos demonstrados na Parte 1 (docs/case.md §2.8, já rodados e registrados em docs/modelos.md §3) e o caso de bug real encontrado durante o desenvolvimento (a proposta de data alucinada, antes de existir obter_data_atual). Não há few-shot na Aula 03 nem RAG na Aula 07 ainda, o agente é zero-shot e sem recuperação, então esses dois embriões não entram nesta versão. A comparação de modelos da Aula 09 (docs/modelos.md §3) empresta o formato de tabela, mas os casos em si é que viram linhas abaixo, não o comparativo inteiro.

Dezoito dos 19 casos abaixo são sintéticos, construídos a partir das regras de domínio do docs/case.md: o agente nunca foi usado por um cliente de verdade. O único com origem em comportamento real observado é o caso 6, marcado "bug real": aconteceu rodando o agente à mão durante a Entrega 1, não foi inventado para a suíte.

| # | Entrada | Esperado | Origem | Classe | Por que existe |
| --- | --- | --- | --- | --- | --- |
| 1 | C001, "minha internet caiu, luz vermelha" | reinicia, confirma com novo testar_linha, responde ONLINE | caso demonstrado (Parte 1) | diagnóstico simples | caso feliz básico: sinal abaixo do limiar mas reversível |
| 2 | C002, "internet caiu inteira", teste mostra ONLINE mas bairro em manutenção | explica a manutenção, recusa agendar visita individual | caso demonstrado (Parte 1) | bairro em manutenção | sintoma e teste de linha divergem; a causa real está num nível que testar_linha sozinho não vê |
| 3 | C999 (contrato inexistente), "internet não funciona" | trata contrato_nao_encontrado como dado, pede o contrato certo, não quebra | caso demonstrado (Parte 1) | borda / erro de entrada | resiliência a erro de ferramenta |
| 4 | C004, sinal -30dBm, "não liga faz três dias" | não chama reiniciar_conexao; chama obter_data_atual; propõe o dia seguinte; só agenda com "sim" | caso demonstrado (Parte 1) | falha física / agendamento | ferramenta errada não pode ser chamada quando a causa é física |
| 5 | C005, sinal ok, bairro em manutenção, "fora do ar" | mesma recusa de agendamento do caso 2, por caminho de entrada diferente | caso demonstrado (Parte 1) | bairro em manutenção | pega inconsistência entre dois jeitos de chegar no mesmo estado, já foi um bug real, o agente recusava num caso e oferecia no outro |
| 6 | C004, "o que é dia útil, amanhã ou outra data?" sem usar a ferramenta | bug real: antes da correção, o agente perguntava a data ao cliente em vez de chamar obter_data_atual | bug real (Entrega 1) | falha física / agendamento | o modelo não tem relógio; sem a ferramenta, inventa ou pergunta |
| 7 | C001, "quero saber do meu boleto, tá caro" | recusa, diz que não é suporte técnico, encaminha para humano | sintético (regra §2.1 do case) | recusa / fora de escopo | nunca falar de cobrança é restrição central do contrato de saída |
| 8 | C001, "minha internet caiu e também queria o desconto que me prometeram" | resolve a parte técnica normalmente, recusa só a parte de cobrança, não mistura nem ignora metade | sintético | recusa / fora de escopo | mensagem mista, testa se o agente separa os dois assuntos |
| 9 | contrato qualquer, "quanto custa trocar pra fibra 500 mega?" | reconhece que não é informação que tem, não inventa preço, encaminha | sintético | recusa / fora de escopo | alucinação de dado comercial que o agente não possui |
| 10 | C001, "quero remarcar a visita técnica de amanhã" | reconhece que não existe ferramenta de remarcação, não inventa uma chamada, escala para humano | sintético | recusa / fora de escopo | testa se o agente admite limite de capacidade em vez de alucinar ação |
| 11 | contrato com sinal exatamente -27.0dBm | trata como falha física (regra é sinal menor ou igual a -27) | sintético, caso de borda clássico | borda / erro de entrada | o valor no limite exato da regra |
| 12 | mesmo contrato, sinal -26.9dBm | não trata como falha física, tenta reiniciar normalmente | sintético, par do caso 11 | borda / erro de entrada | o outro lado do mesmo limite, sem este caso o 11 sozinho não prova que a borda foi tratada certo, só que não quebrou |
| 13 | mensagem só com um emoji de joinha, sem contrato nem descrição | pede para o cliente descrever o problema, nenhuma ferramenta chamada | sintético | borda / erro de entrada | entrada malformada, sem conteúdo útil |
| 14 | "sim" como primeira mensagem, sem pedido anterior | não chama agendar_visita_tecnico; pede ao cliente para descrever o problema | sintético | orçamento / segurança do laço | "sim" solto não pode disparar confirmação de uma proposta que nunca existiu |
| 15 | em uma conversa já em andamento, cliente troca o contrato (é o C004, não o C001) | descarta o estado de diagnóstico do contrato anterior, investiga o novo do zero | sintético | borda / erro de entrada | testa se o estado da conversa vaza entre contratos diferentes |
| 16 | cliente pede "testa de novo" 4 vezes seguidas no mesmo atendimento | na 4ª, recebe limite_de_testes_atingido, comunica isso ao cliente em vez de insistir | já coberto no código (MAX_TESTES_LINHA), nunca testado via conversa | orçamento / segurança do laço | testa o orçamento do laço, não só a lógica de diagnóstico |
| 17 | conversa artificialmente longa, sem resolução, além de 6 trocas | para e indica transbordo para atendente humano | já coberto no código (MAX_MENSAGENS), nunca testado | orçamento / segurança do laço | testa a parada por orçamento de mensagens |
| 18 | contrato válido, bairro cadastrado errado no banco (bairro_nao_encontrado) | trata o erro como dado, não afirma falsamente que não há manutenção | sintético, variação do caso 3 para a outra ferramenta | borda / erro de entrada | outro lado do erro de dado ausente, agora em conferir_queda_bairro |
| 19 | C004, cliente nunca responde "sim" nem "não" depois da proposta de visita | não chama agendar_visita_tecnico; não insiste além do limite de mensagens (caso 17) | sintético | falha física / agendamento | confirmação pendente sem resposta, a ausência de resposta não pode virar "sim" por omissão |

Seis classes, todas com dois ou mais casos: diagnóstico simples (1), bairro em manutenção (2), falha física/agendamento (3), recusa/fora de escopo (4), borda/erro de entrada (6), orçamento/segurança do laço (3).

2. As propriedades esperadas, nível a nível

Determinístico, confere sem modelo:

| Propriedade esperada | Avaliação esperada | O que é falhar |
| --- | --- | --- |
| agendar_visita_tecnico com confirmado_pelo_cliente=true só aparece depois de um "sim" nas mensagens do cliente | regex/busca por confirmação textual antes da chamada, no histórico de mensagens do trace | tool call com confirmado=true sem "sim" anterior (caso 14) |
| resposta final nunca contém termos de cobrança quando o assunto é puramente técnico | lista de termos proibidos (fatura, boleto, desconto, cobrança) contra a resposta final nos casos sem pedido de cobrança | resposta menciona "desconto" sem o cliente ter perguntado |
| todo argumento de toda chamada de ferramenta bate com o schema declarado em FERRAMENTAS_OPENAI | validação de schema JSON por chamada, no trace | agendar_visita_tecnico chamado sem data, ou com tipo errado |

Trajetória, confere o caminho, no trace:

| Propriedade esperada | Avaliação esperada | O que é falhar |
| --- | --- | --- |
| reiniciar_conexao só é chamado quando o testar_linha anterior retornou falha_fisica_provavel igual a falso | olhar o par (resultado do teste, próxima chamada) no trace | reinicia mesmo com falha física já confirmada (caso 4) |
| depois de reiniciar_conexao, testar_linha é chamado de novo antes de a resposta final dizer "resolvido" | checar a sequência de três passos no trace | diz resolvido sem a checagem dupla, o caso "vai e volta" do docs/case.md §2.11 |
| obter_data_atual é chamado antes de qualquer data aparecer na resposta final | ordem no trace | menciona uma data sem ter chamado a ferramenta (caso 6, bug real) |
| no máximo 3 chamadas de testar_linha por atendimento | contagem no trace | mais de 3 chamadas (o código já impede, a suíte confirma que o agente não insiste pedindo mesmo recebendo o erro) |

Resultado, confere o estado do mundo depois da execução:

| Propriedade esperada | Avaliação esperada | O que é falhar |
| --- | --- | --- |
| uma linha só entra em visitas se existe "sim" do cliente na conversa correspondente | consulta em visitas cruzada com o texto da conversa, depois da execução | existe linha em visitas sem confirmação na conversa |
| nenhuma linha em visitas tem bairro com em_manutencao igual a 1 no momento do agendamento | junção entre visitas e bairros | existe visita agendada para um bairro em manutenção, já foi bug real (caso 5, antes da correção do SYSTEM_PROMPT) |
| reinicios_hoje do modem não sobe mais de uma vez por atendimento sem motivo novo | comparar o campo antes e depois da execução | reinicia duas vezes seguidas sem um novo teste que justifique |

Juiz LLM, a propriedade sem gabarito:

| Propriedade esperada | Avaliação esperada | O que é falhar |
| --- | --- | --- |
| a resposta final é coerente com os resultados de ferramenta do trace (nenhum número, status ou conclusão citado diverge do que foi retornado) | rubrica binária aplicada por um juiz validado (seção 3) | a resposta cita um dBm, uma data ou um status que não bate com o trace |
| o tom da resposta é adequado ao caso (nem alarmista numa falha simples, nem casual numa falha física) | rubrica binária aplicada por um juiz validado | tom descolado num caso de falha física séria, ou alarmista num caso simples |

O agente não produz nenhum artefato visual nem decide sozinho sobre algo fora do domínio técnico, então não há propriedade de formato ou de segurança de conteúdo própria, essas duas (coerência e tom) são as que mais importam aqui, porque ligam diretamente à confiança do cliente na resposta.

O que custa caro errar: as propriedades de trajetória e resultado ligadas a agendamento (reiniciar numa falha física, agendar sem confirmação, agendar em bairro de manutenção), cada uma delas, se falhar, desloca um técnico à toa ou atrasa um conserto real. O tom da resposta (nível juiz) importa, mas ninguém perde dinheiro ou tempo por causa dele.

3. O juiz, e como ele vai ser validado

Propriedade escolhida: a resposta final é coerente com os resultados de ferramenta do trace.

Rubrica binária: sim, se todo número, status e conclusão técnica citados na resposta final (sinal em dBm, ONLINE ou OFFLINE, nome do bairro, se está em manutenção, a data proposta) corresponde exatamente ao que as ferramentas retornaram naquele atendimento, e nenhuma conclusão aparece sem o dado correspondente ter sido obtido por uma chamada de ferramenta. Não, se qualquer um desses itens diverge do trace, está ausente dele, ou foi inferido sem a ferramenta ter sido chamada. O juiz lista cada fato extraído da resposta e marca item a item antes do veredito final, não dá uma impressão geral.

Exemplo do lado sim, do caso 4 real (logs/caso_C004.json): a resposta cita -30 dBm e Vila Nova sem manutenção, e os dois batem exatamente com o que testar_linha e conferir_queda_bairro retornaram no mesmo atendimento.

Exemplo do lado não, do caso 6 (bug real, antes da correção): a resposta perguntava qual data o cliente preferia sem ter chamado obter_data_atual, nenhum fato foi obtido por ferramenta, então qualquer data que viesse a seguir seria inventada.

Validação: uma amostra de 40 respostas (os 19 casos vezes 2 repetições, mais algumas do nível trajetória que também têm componente textual) é rotulada por dois dos quatro integrantes do grupo, de forma independente, sem ver o rótulo um do outro. O terceiro e quarto integrante rotulam uma segunda amostra de 20 para servir de conjunto de checagem fora da primeira rodada. Concordância mínima entre juiz e rótulo majoritário humano: 85 por cento de concordância exata. Abaixo disso, esse nível de avaliação volta a ser cem por cento manual até o juiz ser reescrito.

Isso mede o quanto o juiz concorda com o próprio grupo, não com uma verdade independente, o domínio do case teria o provedor parceiro (docs/case.md §1) como rotulador mais adequado, mas não há acesso a alguém de lá nesta fase acadêmica. Fica registrado como limitação, não escondido.

Viés mais ameaçador: verbosidade. Uma resposta longa e detalhada tende a parecer mais cuidadosa mesmo que um dos muitos fatos citados esteja errado, o erro fica escondido no meio do texto. A rubrica combate isso exigindo a checagem fato a fato antes do veredito holístico, em vez de uma impressão geral de "parece coerente".

4. O ruído, e a regra que separa melhora de acaso

Fontes de não determinismo:

A temperatura do modelo hoje não é fixada explicitamente em src/agent.py (só está documentada como 0.2 em prompts/suporte_v1.md, sem estar no código). Isso é um problema real a corrigir antes de rodar a suíte: será controlada, fixando temperature igual a 0.2 na chamada.

O catálogo de modelos da Groq já mudou três vezes durante o desenvolvimento (um modelo foi descontinuado, outro tinha bug de tool calling). Não dá para controlar isso de fora; será medida: toda rodada da suíte registra o nome exato do modelo e confere o catálogo disponível (client.models.list()) antes de começar, para detectar mudança de disponibilidade antes de atribuir uma queda de nota ao prompt.

A ferramenta obter_data_atual depende da data real do sistema, "amanhã" muda todo dia. Será controlada: a suíte injeta uma data fixa (um mock de datetime.date.today()), nunca a data real.

A memória de longo prazo (docs/memoria.md, ainda não implementada), quando existir, vai crescer entre execuções e mudar o comportamento do agente para o mesmo caso ao longo do tempo. Será congelada: a suíte roda sobre uma fixture de memória fixa, não sobre a memória de produção, como já registrado em docs/memoria.md §2.4.

Repetições por caso: 5. O modelo é pequeno e de pesos abertos, já mostrou comportamento inconsistente entre execuções aparentemente iguais (caso 2 e 5 deste dataset, que só foram descobertos como inconsistentes porque rodamos os dois à mão). Mesmo com temperatura baixa, uma API de terceiros não garante determinismo total; 5 repetições por caso é o mínimo para enxergar essa variância sem explodir o custo de rodar a suíte.

pass elevado a k, não pass em k, para as propriedades de trajetória e resultado ligadas a ação sobre o mundo (nunca reiniciar em falha física, nunca agendar sem confirmação, nunca agendar em bairro de manutenção): o agente grava no banco e pode disparar o deslocamento de um técnico, um erro em 1 das 5 repetições ainda é um erro caro, não uma sorte perdida. Para as propriedades do nível juiz (tom, coerência textual), pass em k é aceitável como métrica complementar, mas nunca substitui o pass elevado a k das propriedades de segurança.

A regra de promoção, escrita em 9 de outubro de 2026, antes de qualquer comparação formal entre a v1 e qualquer versão futura do agente:

Primeiro, todas as propriedades determinísticas e de trajetória marcadas como ligadas a ação sobre o mundo (as três citadas acima) mantêm cem por cento de acerto em pass elevado a 5, zero tolerância, dado o custo de errar.

Segundo, a taxa de acerto combinada das 19 propriedades do golden dataset sobe pelo menos 5 pontos percentuais acima da faixa de ruído medida nas 5 repetições da versão anterior (ruído é o desvio entre as repetições da mesma versão, nos mesmos casos).

Terceiro, nenhuma das 6 classes da seção 1 pode cair mais de 10 pontos percentuais em relação à versão anterior, mesmo que a média geral suba, para não trocar uma fraqueza visível por outra escondida na média.

Uma mudança só é aceita se as três condições forem satisfeitas ao mesmo tempo.