<!-- Transcrição fiel do PDF "Memória — Agente de Suporte Técnico Doméstico.pdf" (Exercício 8, material do grupo). O PDF foi removido do repositório; o conteúdo está aqui. A pontuação é a do original. -->

# Memória — Agente de Suporte Técnico Doméstico

## Decisão 2 — Como o agente esquece

(Decidida primeiro, como sugerido: a lista de exclusão restringe a de inclusão.)

### 2.1 Contradição — o fato que mudou

Exemplo real do domínio: o prazo para agendar visita técnica era "até o dia seguinte" e passou a ser "até 48h" numa atualização de política comercial. Outro caso do mesmo tipo: a lista de modems compatíveis com um plano muda quando o provedor atualiza a linha de equipamentos, e o fato antigo ("modem X é compatível com o plano Y") continua tão parecido, por similaridade, quanto o novo.

Regra de desempate: todo fato semântico carrega carimbo de tempo obrigatório; a leitura aplica `max()` sobre o carimbo, nunca deixa o modelo decidir por similaridade. O descarte é registrado — quando um fato perde para um mais novo, grava-se um log do tipo fato "prazo_visita=1_dia" desativado em favor de "prazo_visita=48h", motivo: atualização de política, em 2026-08-01.

### 2.2 Decaimento — o fato que envelheceu sem ser contradito

Corte: 180 dias para um registro episódico (resumo de atendimento). Justificativa: causas de falha de rede mudam com a evolução da infraestrutura do provedor (troca de equipamento, atualização de fibra num bairro) um atendimento antigo com sintoma parecido pode levar a um diagnóstico desatualizado depois desse período.

Efeito: rebaixado, não removido sai do topo do índice de similaridade (não compete mais com atendimentos recentes na recuperação), mas continua acessível para estatística e auditoria de longo prazo do provedor. Isso importa para a Decisão de remoção abaixo: rebaixar não é apagar, então um registro rebaixado ainda precisa ser alcançado se o titular pedir exclusão.

### 2.3 Remoção — o titular solicitou

Situação do domínio: cliente cancela o contrato e pede exclusão de dados (LGPD). O identificador (`id_contrato`) pode ter caído em mais estruturas do que as três memórias sugerem:

- memória episódica — resumos de atendimento vinculados ao `id_contrato`;
- memória semântica — registro de cadastro sincronizado (contrato, endereço, modem);
- checkpoint — atendimentos em aberto ou arquivados que ainda referenciam o contrato;
- log de ferramentas — toda chamada de `testar_linha`, `reiniciar_conexao`, `agendar_visita_tecnica` grava `id_contrato` como argumento;
- memória procedural — só entra na lista se alguma regra aprendida citar o contrato especificamente (raro: ex. "contrato 48219 tem histórico de falso positivo no teste de sinal"); a maioria das regras procedurais é genérica e não cita cliente.

Verificação, independente da remoção: grava a exclusão, depois varre episódica + semântica + checkpoints arquivados + logs procurando o `id_contrato`, e só declara concluído com zero ocorrências nessa varredura.

Limitação a declarar: se o índice de similaridade (embeddings da memória episódica) não suporta exclusão pontual, a remoção completa exige reconstrução do índice numa janela de manutenção até lá, o dado continua fisicamente no índice vetorial mesmo marcado como removido na tabela relacional. Isso é suficiente para privacidade de consulta comum e para custo, mas não é suficiente se o motivo da remoção for um incidente de segurança que exige que o dado deixe de existir imediatamente.

## Decisão 1 — Como o agente lembra

### 1.1 Os dois níveis, no domínio do case

| | curto prazo | longo prazo |
|---|---|---|
| o que é | um atendimento (do "oi" do cliente até a resolução ou o que atravessa escalonamento) | atendimentos e contratos |
| conteúdo | system prompt, objetivo ("resolver o chamado do contrato X"), testes já rodados nesse atendimento, resultado do último teste, horário de visita oferecido e ainda não confirmado | episódica, semântica, procedural (§1.3) |
| persistido como | checkpoint — um registro por `id_atendimento` | índice de resumos, tabela de cadastro, texto no system prompt |
| lido | uma vez, ao retomar o atendimento (ex.: cliente confirma a visita horas depois) | por relevância, a cada teste/decisão do atendimento |
| acesso | por `id_atendimento` | por relevância (episódica) ou por `id_contrato` (semântica) |
| ciclo de vida | morre quando o atendimento fecha (mas é arquivado, não descartado, até o corte do §2.2 valer para ele) | acumula |

O checkpoint guarda especificamente: `id_contrato`, lista de testes já tentados nesse atendimento (para não repetir `testar_linha` inutilmente), resultado do último teste, contador de testes usados (contra o `MAX_TESTES`), e a flag `aguardando_confirmacao_cliente` com o horário oferecido. Isso responde às três perguntas do exercício: o atendimento é retomável sem repetir o reinício já aplicado (porque "já reiniciei" fica gravado); uma confirmação de visita que chega horas depois encontra o horário oferecido salvo, sem precisar oferecer de novo; e um atendimento que travou pode ser recarregado com o mesmo estado para depuração.

### 1.2 O orçamento da janela

| Fonte | Teto (tokens) | Descartado primeiro? |
|---|---|---|
| system prompt | ~300 | não |
| definição das ferramentas | ~200 | não |
| checkpoint do atendimento atual | ~150 | não |
| trajetória (mensagens deste atendimento) | ~800 | trunca as **mais antigas**, mas resume tool calls passadas para só o resultado, não a chamada inteira |
| trechos recuperados de memória de longo prazo | ~600 | **primeiro a cair** quando o total estoura |

Total ~2.000 tokens. O que cai primeiro é a memória de longo prazo recuperada (histórico de atendimentos parecidos), não a trajetória do atendimento corrente perder contexto do que já foi tentado *agora* faz o agente repetir pergunta ao cliente; perder um atendimento antigo parecido só degrada a qualidade do diagnóstico, não trava o fluxo.

### 1.3 As três memórias de longo prazo

| Tipo | O que guarda no case | Estrutura | Como é recuperada |
|---|---|---|---|
| episódica | resumo de 2-3 linhas de atendimentos anteriores do mesmo contrato ou bairro (sintoma, diagnóstico, resolução) | índice por similaridade (embedding do resumo) | por similaridade do sintoma relatado, filtrado por `id_contrato` ou bairro |
| semântica | cadastro do cliente: modelo do modem, endereço/bairro, plano contratado, status do contrato | chave-valor | por chave (`id_contrato`) |
| procedural | regras de diagnóstico revisadas pela operação ex.: "sinal óptico abaixo de X dBm e bairro em manutenção ativa → não sugerir visita individual, aguardar manutenção geral" | texto no system prompt | sempre presente, não é "recuperada" por consulta |

### 1.4 Quem escreve, e o que não entra

- **Episódica:** o próprio agente escreve, automaticamente, ao fechar cada atendimento 1 registro por atendimento, 2-3 linhas.
- **Semântica:** não é o agente quem escreve é extraída por regra em código a partir do sistema de cadastro do provedor, sincronizada quando há mudança de contrato, não a cada atendimento.
- **Procedural:** só entra por revisão humana da equipe de operação (NOC), nunca escrita automática do agente evita que uma regra aprendida de um diagnóstico errado vire regra permanente sem checagem.

O que o sistema **não** guarda:

- **Dado sensível:** nem senha de Wi-Fi nem CPF/documento do cliente viram memória de longo prazo do agente ambos continuam só no sistema de cadastro/configuração, consultados via ferramenta quando necessário, nunca persistidos fora dele.
- **Conteúdo não verificado:** a transcrição bruta do WhatsApp não vira registro episódico direto só o resumo gerado depois que o atendimento realmente fecha, para não gravar como fato um diagnóstico intermediário que foi corrigido no meio da conversa.
- **O que é derivável:** o valor numérico do teste de sinal (dBm) não entra na memória de longo prazo é derivável rodando o teste de novo; só o resumo qualitativo do atendimento é guardado, o número bruto fica no log do próprio sistema de monitoramento da rede.

## O que o agente não guarda, e o que ele perde quando perde

O agente não guarda dado sensível de identificação, conteúdo não verificado de uma conversa em andamento, nem valor bruto derivável de teste técnico. O preço disso: se dois clientes relatam o mesmo sintoma físico incomum (ex.: um tipo raro de interferência), e o valor bruto do teste não foi guardado, o agente não consegue comparar os dois casos numericamente depois, só pelo resumo qualitativo. Isso é aceito porque o valor bruto é barato de re-obter (basta rodar o teste de novo), e guardá-lo desnecessariamente é dívida de privacidade sem ganho real de diagnóstico.

O sistema também deixa de ser reprodutível por construção: o mesmo relato de sintoma, no mesmo modelo, pode gerar diagnóstico diferente amanhã, porque a memória episódica ganhou mais casos parecidos ou porque um fato semântico foi atualizado por contradição (§2.1). Isso é consequência da Decisão.
