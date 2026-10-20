# Model Card — Agente de Suporte Técnico Doméstico

> **Status do documento:** quarta versão. A segunda fechou as lacunas L02 a L09, L12 e parte da L14 da auditoria inicial. A terceira atualizou o documento para a Parte 2 (grafo LangGraph, RAG, memória e aprovação humana). Esta alinha os números e as regras ao código final: 57 testes, dez casos reais, triagem de entrada incompleta em código e onze motivos de término (ver seção "Lacunas" ao final).

Este documento descreve a finalidade, as capacidades, a autoridade, os dados tratados, os riscos e os controles do Agente de Suporte Técnico Doméstico. Cada afirmação verificável deve estar associada a uma evidência consultável no repositório ou em uma configuração externa. Quando não há evidência suficiente, o documento declara explicitamente uma lacuna.

## 1. Identificação

**Afirmação**

O sistema é um agente de inteligência artificial desenvolvido para realizar diagnóstico e suporte técnico doméstico de problemas de conexão à internet. O projeto utiliza um modelo de linguagem para interpretar a solicitação do cliente, selecionar ferramentas e formular uma resposta.

O sistema é desenvolvido em Python e possui código em `src/`, instruções em `src/prompts/`, documentação em `docs/` e registros de execução em `logs/`.

**Responsáveis**

- Integrantes responsáveis pelo desenvolvimento: LACUNA — inserir os nomes completos dos integrantes do grupo.
- Responsável pela aprovação das mudanças: LACUNA — definir quem revisa e aprova alterações no agente.
- Responsável por suspender o sistema em caso de falha: LACUNA — definir uma pessoa responsável e um procedimento de interrupção.

**Evidências**

- `README.md`: identificação do projeto e instruções de execução.
- `src/grafo.py`: grafo do atendimento; `src/agent.py`: ponto de entrada e log.
- Histórico de commits do GitHub: https://github.com/MariaCoelhoM/Agente_de_llm/commits/main

**LACUNA:** não há evidência suficiente, neste documento, de uma versão formal do sistema, de uma política de releases ou da designação de responsáveis pela operação. Para corrigir, registrar os responsáveis, identificar o commit avaliado e criar uma tag de versão.

## 2. Finalidade

**Afirmação**

O objetivo do agente é investigar problemas de conexão à internet, executar testes automatizados na linha do cliente, tentar resolver problemas remotamente e indicar a necessidade de atendimento humano quando não consegue solucionar a ocorrência.

A entrada do programa consiste em um identificador de contrato simulado e uma mensagem descrevendo o problema. O resultado é apresentado no terminal, acompanhado do motivo de encerramento e do caminho do registro da execução.

Usos fora de escopo:

- Resolver questões de cobrança, faturas ou cancelamentos sem atendimento humano.
- Tomar decisões comerciais ou financeiras em nome do provedor.
- Executar operações administrativas não previstas nas ferramentas do projeto.
- Tratar os dados simulados como se fossem dados de clientes reais.
- Ser utilizado em produção sem avaliação de segurança, privacidade e confiabilidade.

**Evidências**

- `README.md`: seções “O problema em uma frase”, “Como usar” e descrição do que o sistema não faz.
- `docs/case.md`: descrição do caso de uso e dos cenários de teste.
- `src/agent.py`: fluxo de atendimento e interação com o modelo.
- `src/prompts/suporte_v2.md`: instruções de comportamento do agente.

**LACUNA:** as restrições descritas no prompt não comprovam, isoladamente, que todas as utilizações fora de escopo são bloqueadas tecnicamente. É necessário testar cada restrição e identificar os pontos de aplicação no código.

## 3. Autoridade

### 3.1 Escopo autorizado

O agente pode interpretar a solicitação do usuário, consultar os dados simulados associados ao contrato, executar as ferramentas disponibilizadas pelo projeto, tentar solucionar problemas de conexão e propor um agendamento conforme as regras de negócio implementadas.

O agente não deve realizar operações que não estejam previstas nas ferramentas disponibilizadas nem ultrapassar os limites definidos para cada ferramenta.

**Evidências**

- `src/agent.py`: definição do agente, instruções, ferramentas disponibilizadas e fluxo de execução.
- `src/tools.py`: implementação das ferramentas e validações operacionais.
- `src/prompts/suporte_v2.md`: regras de comportamento.
- `README.md`: descrição dos cenários e do comportamento esperado.

### 3.2 Matriz de autoridade e ponto de aplicação

| Limite ou controle | Ponto de aplicação | Evidência e situação |
|---|---|---|
| Consultar apenas contratos previstos nos cenários simulados | Código e banco de dados | `src/db.py` e `src/tools.py`. Confirmado: `tests/test_limites_autoridade.py::test_contrato_inexistente_retorna_erro_como_dado` roda as três ferramentas que recebem contrato contra C999 e exige o erro `contrato_nao_encontrado`. |
| Limitar o atendimento a seis voltas do agente | Código | `src/config.py` (`MAX_VOLTAS_AGENTE`), aplicado por `src/guardas.py::verificar_orcamento` no nó `agente`. Confirmado por `tests/test_grafo.py::test_limite_de_voltas`; o atendimento termina com `limite_de_voltas` e encaminha para humano. |
| Limitar a quantidade de testes de linha | Código | `src/grafo.py`, nó `ferramentas`. Confirmado por `tests/test_grafo.py::test_limite_de_testes_de_linha`: a quarta chamada no mesmo atendimento recebe `limite_de_testes_atingido`. Além disso há limite de 8 chamadas de ferramenta, detector de laço, teto de 12000 tokens e de 120 s (`docs/grafo.md` §5). |
| Não agendar sem confirmação explícita | Código, estrutural: o modelo não tem a ferramenta que agenda | `src/grafo.py`. O modelo só tem `propor_visita` (validação pura). O agendamento acontece no nó `agendar`, depois do nó `aprovacao`, que pausa com `interrupt` e só segue com a resposta de uma pessoa (aprovar, rejeitar, editar ou expirar). Isso substitui a varredura textual da palavra "sim" (`cliente_confirmou`), que aceitava qualquer "sim" da conversa, inclusive anterior à proposta. Testado em `tests/test_grafo.py` (modelo sem a ferramenta, chamada indevida recusada, rejeitar, expirar e edição inválida não agendam). |
| Não agendar visita individual durante manutenção no bairro | Código e dados | `src/tools.py` e `src/db.py`. Confirmado por `tests/test_limites_autoridade.py::test_nao_agenda_em_bairro_em_manutencao`, que reproduz a condição do caso C005/C002. |
| Não realizar operações além das ferramentas permitidas | Ausência de ferramenta e validação no código | `src/tools.py::FUNCOES` é o inventário do que o modelo enxerga: `obter_data_atual`, `testar_linha`, `conferir_queda_bairro`, `reiniciar_conexao`, `propor_visita` e `consultar_base_conhecimento`. `agendar_visita_tecnico` fica em `FUNCOES_INTERNAS`, fora do alcance do modelo. Uma chamada a qualquer outro nome retorna `ferramenta_desconhecida` (`src/grafo.py`, nó `ferramentas`), sem execução de código arbitrário; o contrato da sessão substitui o que o modelo digitar. Testado em `tests/test_grafo.py` (`test_modelo_chamando_agendar_por_fora_nao_agenda`, `test_contrato_da_sessao_vence_o_que_o_modelo_digita`). |
| Limitar gastos com o provedor do modelo | Plataforma | A conta usada é do tier gratuito da Groq, sem forma de pagamento cadastrada — ver `docs/modelos.md` §5. Como não há cartão associado, não há caminho para gerar cobrança; o teto de gasto configurável do console só existe em planos pagos. Falta só uma conferência de um minuto, de quem mantém a conta: confirmar em Settings → Billing que nenhum cartão foi adicionado. |
| Restringir o acesso da credencial | Credencial | `docs/modelos.md` §5: a Groq não oferece escopo granular de chave no tier gratuito — a chave vale para a conta inteira. Não é uma lacuna de verificação, é uma característica do provedor; documentado como tal, não como pendência. |
| Suspender o agente em caso de comportamento inadequado | Operação e plataforma | LACUNA — documentar procedimento, responsável e forma de revogar credenciais ou interromper a execução. Fora do escopo desta rodada de correções: depende de uma decisão do grupo sobre quem assume esse papel, não de código ou de documentação do provedor. |
| Aprovar operações sensíveis por um humano | Código e procedimento operacional | Implementado na Parte 2: o nó `aprovacao` pausa o grafo com `interrupt` e mostra a ação exata, a data e a consequência; aceita aprovar, rejeitar, editar (data validada) ou expirar (prazo de 900 s, sem agendar e com encaminhamento a humano). Ver `docs/humano.md`. Testado em `tests/test_grafo.py`. Em aberto: quem é a pessoa que responde na operação real (L11). Na demonstração quem responde é a pessoa que roda o programa. |

### 3.3 Ações proibidas

O agente não deve:

- Agendar uma visita sem confirmação válida do cliente.
- Agendar uma visita individual em um bairro em manutenção.
- Continuar indefinidamente uma conversa que não consegue resolver.
- Tratar um contrato inexistente como um registro válido.
- Executar ações que não tenham sido disponibilizadas ou autorizadas pelo sistema.
- Utilizar dados reais de clientes sem autorização, finalidade definida e controles de privacidade adequados.

**Evidências**

- `src/tools.py`: funções que executam as operações e verificam condições.
- `src/agent.py`: fluxo de execução e limites de mensagens e testes.
- `src/db.py`: dados e condições dos cenários simulados.
- `docs/case.md`: casos C001, C002, C004, C005 e C999.

### 3.4 Credenciais, gastos e suspensão

A execução recebe configurações por variáveis de ambiente, incluindo `LLM_BASE_URL`, `OPENAI_API_KEY` e `LLM_MODEL`, conforme as instruções do projeto.

A existência dessas variáveis não comprova, por si só, os privilégios efetivos da credencial, a região de processamento, o orçamento disponível ou os limites de consumo configurados — essas informações foram buscadas na documentação do provedor e estão registradas em `docs/modelos.md` §5.

- **Credencial:** a Groq não oferece escopo granular de chave no tier gratuito — a chave de API vale para a conta inteira, não para um recurso específico. Não há como restringir mais do que isso dentro do que o provedor oferece; o controle possível é operacional (rotacionar e revogar a chave se vazar), não técnico.
- **Limite de gasto:** a conta é do tier gratuito, sem cartão cadastrado. A Groq só oferece teto de gasto configurável em planos pagos; sem forma de pagamento associada, não existe caminho para a execução gerar cobrança. Resta uma conferência manual de um minuto — confirmar em Settings → Billing que nenhum cartão foi adicionado — que ainda não foi feita por ninguém do grupo.
- **Falha de controle:** interromper a execução e impedir novas ações até que a falha seja investigada. O grafo encerra e registra o motivo (`motivo_parada`) em onze situações (`docs/grafo.md` §5). Cobertos por teste: `limite_de_voltas`, `limite_de_ferramentas` (via teste de linha), `laco_detectado`, `tokens_esgotados`, `erro_fatal_llm`, `recursion_limit` e `aprovacao_expirada` (`tests/test_grafo.py`). O limite de 25 passos é declarado em `src/config.py` porque o padrão do LangGraph 1.2.16 é 10007 (`docs/grafo.md` §4). `entrada_incompleta` é coberta por `test_entrada_sem_sintoma_pede_detalhes_sem_chamar_o_modelo`. Sem teste: `tempo_esgotado`.
- **Suspensão:** LACUNA — definir quem pode interromper o processo e revogar a credencial utilizada. Depende de uma decisão do grupo sobre papéis, não de código.

## 4. Ferramentas e integrações

**Afirmação**

O agente utiliza ferramentas Python disponibilizadas pelo próprio projeto e um provedor de modelo de linguagem configurado por variáveis de ambiente. O banco de dados simulado fornece informações necessárias para os cenários de atendimento.

**Inventário**

| Ferramenta ou integração | Finalidade | Permissões e evidências |
|---|---|---|
| Modelo de linguagem | Interpretar a solicitação, orientar o fluxo e formular respostas | `src/llm.py::ClienteLLM.chamar`. Endpoint e modelo vêm de `LLM_BASE_URL` e `LLM_MODEL` (hoje: Groq, `qwen/qwen3.8-27b`, `docs/modelos.md` §4); temperatura fixa em 0,2 (`src/config.py`). Lê o contexto da conversa, não escreve em nada diretamente: toda escrita passa pelas ferramentas abaixo. Tentativas automáticas só para limite de taxa, conexão e timeout. |
| `obter_data_atual` | Saber a data de hoje, sem relógio próprio | `src/tools.py`. Leitura, sem argumento, sem efeito. |
| `testar_linha` | Consultar o status e o sinal do modem | `src/tools.py`. Leitura em `dados/provedor.db`, sem escrita. |
| `conferir_queda_bairro` | Verificar manutenção geral no bairro do cliente | `src/tools.py`. Leitura em `dados/provedor.db`, sem escrita. |
| `reiniciar_conexao` | Tentar solucionar problemas remotamente | `src/tools.py`. Escrita reversível: `UPDATE` em `modems.status` e `modems.reinicios_hoje`, só no banco simulado local. Recusa se detecta falha física (sinal ≤ −27dBm). |
| `propor_visita` | Propor visita técnica | `src/tools.py`. Validação pura, sem escrita: data de hoje ou amanhã, contrato existente, bairro fora de manutenção. O grafo recusa a proposta sem teste de linha prévio e depois de uma recusa do cliente. |
| `consultar_base_conhecimento` | Consultar manuais e políticas | `src/rag.py`. Leitura; BM25 sobre `dados/corpus/`, só documentos vigentes, com portão de suficiência (`docs/rag.md`). |
| `agendar_visita_tecnico` | Registrar uma visita técnica | `src/tools.py`. Escrita irreversível no domínio simulado: `INSERT` em `visitas`, só no banco local. Não está na lista do modelo: só o nó `agendar` a chama, com `confirmado_pelo_cliente=True`, depois da aprovação (`src/grafo.py`). Idempotente (chave de contrato e data, índice único) e valida a data (entre hoje e hoje + 14 dias). Recusa se o bairro está em manutenção. |
| Banco de dados simulado | Armazenar contratos e informações dos cenários | `src/db.py`, SQLite local em `dados/provedor.db`. O README informa que o banco é gerado localmente e não é versionado (está em `.gitignore`). |
| Memória e checkpoints | Memória entre atendimentos e retomada da pausa de aprovação | `src/memoria.py` grava em `dados/memoria.db` (fatos por contrato, episódios, descartes); o LangGraph grava o estado em `dados/checkpoints.db`. Ambos fora do Git (`.gitignore`). Escrita feita só pelo código, a partir do que as ferramentas retornaram (`docs/memoria.md`). |
| Registros de execução | Registrar a trajetória das ferramentas, a pausa de aprovação e a saída validada | `src/agent.py` e diretório `logs/`. Retenção de 30 dias via `scripts/limpar_logs_antigos.py`. |

**Servidores MCP:** confirmado por inspeção de `requirements.txt` — não há dependência de nenhum pacote MCP, e nenhuma ferramenta abre conexão de rede própria. Nenhum servidor MCP está configurado nesta entrega.

**Permissões de escrita e envio a terceiros:** confirmado por inspeção de `src/tools.py`, `src/grafo.py` e `src/memoria.py` — `reiniciar_conexao` e `agendar_visita_tecnico` escrevem só em `dados/provedor.db`, e o código do sistema escreve em `dados/memoria.db`, `dados/checkpoints.db` e `logs/`, todos SQLite ou arquivos locais. Nenhuma ferramenta faz requisição de rede própria; o único tráfego de rede do sistema é a chamada ao provedor do modelo (Groq), feita pela biblioteca `openai` dentro de `src/llm.py`. Não há envio de dado a nenhum outro serviço de terceiro.

## 5. Modelo e provedor

**Afirmação**

O agente utiliza um modelo de linguagem configurado por variáveis de ambiente. O projeto prevê as configurações `LLM_BASE_URL`, `OPENAI_API_KEY` e `LLM_MODEL`, permitindo configurar o endpoint, a credencial e o identificador do modelo.

**Evidências**

- `.env.example`: variáveis esperadas para configurar o acesso ao modelo.
- `src/llm.py`: inicialização e chamadas ao modelo.
- `docs/modelos.md`: análise e escolha do modelo.

**Informações que precisam ser comprovadas**

- Nome exato do provedor efetivamente utilizado: Groq (`docs/modelos.md` §4).
- Identificador exato e versão datada do modelo: `qwen/qwen3.8-27b`, confirmado via `client.models.list()` na conta usada (`docs/modelos.md` §4); a Groq não publica uma data de versão própria para esse identificador — a data em que o grupo conferiu o catálogo é a que consta no histórico de commits de `docs/modelos.md`.
- Data em que a versão do modelo foi verificada: ver o commit que introduziu a seção "A decisão" em `docs/modelos.md` — este model card não duplica a data para não ter duas fontes da mesma informação.
- Região geográfica de processamento: Estados Unidos — a Groq retém os dados de monitoramento em buckets do Google Cloud Platform localizados nos EUA (`docs/modelos.md` §5, fonte: console.groq.com/docs/your-data).
- Política de retenção das entradas e saídas no provedor: por padrão a Groq não retém dado de inferência; a exceção é monitoramento de confiabilidade/abuso, por até 30 dias, desativável com Zero Data Retention (`docs/modelos.md` §5).
- Condições de uso dos dados para treinamento pelo provedor: **ainda LACUNA** — a documentação consultada (console.groq.com/docs/your-data) cobre retenção, não uso para treino; não há confirmação num sentido nem no outro, e não deve ser inferida.
- Existência de limites de consumo e de orçamento: sem limite de gasto configurável no tier gratuito usado (sem cartão cadastrado); limites de taxa (requisições por minuto) existem e variam por modelo, não foram medidos sistematicamente nesta entrega (`docs/modelos.md` §4, item 3, menciona a suspeita qualitativa).

Não se deve inferir o provedor, a versão ou a localização dos dados somente a partir do nome de uma variável de ambiente — por isso as respostas acima citam a fonte (commit, documentação oficial do provedor) em vez de assumir a partir de `LLM_BASE_URL`.

## 6. Dados

### 6.1 Fontes e inventário

**Afirmação**

O projeto utiliza dados simulados de contratos e ocorrências para testar o comportamento do agente. Os casos incluem situações em que o problema pode ser resolvido remotamente, divergência entre o estado informado pelo sistema e o relato do cliente, falha física, manutenção no bairro e contrato inexistente.

**Evidências**

- `src/db.py`: estrutura e geração dos dados simulados.
- `README.md`: descrição dos cenários e geração do banco.
- `docs/case.md`: especificação dos casos de teste.
- `src/agent.py`: recebimento dos argumentos, montagem do contexto e chamadas ao modelo.
- `logs/`: registros de execução.

### 6.2 Inventário de dados pessoais

| Dado ou categoria | Finalidade | Local em que entra ou fica | Base legal e retenção |
|---|---|---|---|
| Identificador do contrato | Localizar o registro simulado | Entrada do programa, banco, contexto de execução e `logs/caso_<contrato>.json` | Dados sintéticos no ambiente acadêmico. Retenção local: até 30 dias (`scripts/limpar_logs_antigos.py`, `docs/modelos.md` §5). Para dados reais, ainda seria preciso avaliar a base legal aplicável. |
| Mensagem do cliente | Entender e classificar o problema | Entrada do programa, contexto enviado ao modelo, `logs/caso_<contrato>.json` (`mensagem_inicial`), checkpoints do LangGraph e, em até 200 caracteres, o episódio da memória (`sintoma`) | Vai para o modelo, para o log, para os checkpoints e (resumida) para a memória. Retenção local do log: até 30 dias (`scripts/limpar_logs_antigos.py`). Episódios da memória saem da janela do agente depois de 180 dias, mas ficam arquivados até uma remoção por titular (`remover_titular`). Retenção no provedor: até 30 dias de monitoramento de abuso, desativável com Zero Data Retention (`docs/modelos.md` §5). Base legal continua LACUNA se um dia forem usadas mensagens reais. |
| Nome do cliente, se presente no cadastro | Identificar o registro simulado | `src/db.py`, coluna `clientes.nome` | Confirmado por inspeção do código: **nenhuma ferramenta em `src/tools.py` consulta ou retorna essa coluna** — `conferir_queda_bairro` e `agendar_visita_tecnico` selecionam só `bairro` de `clientes`, nunca `nome`. O nome não chega ao modelo nem ao log. Fica como dado morto no banco simulado; se um dia for usado para dados reais, vale avaliar se precisa continuar existindo no schema. |
| Bairro | Verificar a condição de manutenção e a possibilidade de agendamento | Banco simulado, contexto enviado ao modelo (retorno de `conferir_queda_bairro`) e `logs/caso_<contrato>.json` | Confirmado: vai para o modelo e para o log, porque a decisão de recusar agendamento em manutenção depende disso. Mesma retenção de 30 dias das linhas acima. Para dados reais, avaliar necessidade e prazo seria preciso. |
| Endereço MAC do modem | Identificar o equipamento ou consultar informações técnicas, se utilizado no fluxo | `src/db.py`, coluna `modems.mac` | Confirmado por inspeção do código: `testar_linha` faz `SELECT *` na tabela `modems` (traz o MAC para dentro da função), mas o dicionário retornado só inclui `contrato`, `status`, `sinal_dbm` e `falha_fisica_provavel` — o MAC nunca sai da função, não chega ao modelo nem ao log. |
| Resultado dos testes de conexão | Diagnosticar a ocorrência | Retorno de `testar_linha`, contexto do agente e `logs/caso_<contrato>.json` | Confirmado: `status`, `sinal_dbm` e `falha_fisica_provavel` vão para o modelo e para o log. Retenção local: até 30 dias (`scripts/limpar_logs_antigos.py`). |
| Argumentos e resultados das ferramentas | Permitir auditoria da trajetória da execução | `logs/caso_<contrato>.json`, campo `trajetoria` | Grava `nome`, `args` e `resultado` de cada chamada, a decisão humana e o motivo de término; nunca nome do cliente nem MAC. Prazo de retenção: 30 dias, por `scripts/limpar_logs_antigos.py`. Controle de acesso: o mesmo do repositório Git; aceitável só porque o dado é simulado. |
| Saída validada do agente | Informar o resultado do atendimento | Terminal e `logs/caso_<contrato>.json`, campo `saida` (`resultado`, `fontes`, `suficiente`) | Gerada em `src/grafo.py` (nó `finalizar`) e validada por `src/schemas.py`. Mesma retenção e mesmo controle de acesso do log. |
| Credencial de acesso ao provedor | Autenticar as chamadas ao modelo | Variável de ambiente `OPENAI_API_KEY`, lida por `src/llm.py` (o `.env` é carregado por `src/config.py`) | Não registrada nos logs — confirmado por inspeção: nenhum campo de `registro` em `src/agent.py` grava variável de ambiente. `.gitignore` agora exclui `.env` do repositório (antes não havia `.gitignore`). Rotação e revogação continuam dependendo do console do provedor; sem procedimento formal definido pelo grupo. |

### 6.3 Fluxo dos dados

1. **Entrada:** o contrato simulado e a descrição do problema são fornecidos ao programa.
2. **Consulta:** o agente utiliza as ferramentas disponíveis para recuperar informações e executar diagnósticos.
3. **Contexto do modelo:** informações da solicitação e resultados das ferramentas podem compor as mensagens enviadas ao provedor.
4. **Execução:** argumentos e resultados das ferramentas são registrados conforme o mecanismo de logging implementado.
5. **Saída:** a resposta final é apresentada ao usuário e pode ser gravada no log.

**Evidências:** `src/agent.py`, `src/tools.py`, `src/db.py` e `logs/`.

**Verificado por inspeção do código:** o contexto enviado ao modelo é composto do prompt (`src/prompts/suporte_v2.md`), das regras procedurais (`src/prompts/procedural.md`), do contrato da sessão, da data, de um bloco de histórico do cliente vindo da memória (no máximo 500 tokens, marcado como não confirmado), da mensagem do cliente, do retorno exato de cada ferramenta e dos trechos do manual que a consulta devolver (`src/grafo.py`, função `_mensagens_para_o_modelo`). Nenhuma ferramenta retorna nome do cliente ou endereço MAC (ver acima), então esses campos nunca chegam ao provedor, ao log, à memória nem aos checkpoints. O log grava a trajetória, a decisão humana, o motivo de término e a saída validada, mais `timestamp`, `commit`, `modelo` e `temperature`. O destino geográfico dos dados enviados ao modelo é os Estados Unidos (`docs/modelos.md` §5). A remoção por titular apaga o contrato da memória, dos checkpoints e dos logs (`src/memoria.py::remover_titular`), e `scripts/varrer_contrato.py` confere o resultado de forma independente.

### 6.4 Base legal e minimização

Para dados pessoais reais, a base legal deve ser avaliada conforme a finalidade e as circunstâncias do tratamento, nos termos do artigo 7º da LGPD. Não é possível declarar automaticamente que o consentimento é a única base aplicável, nem afirmar que outra base se aplica sem analisar o caso concreto.

A implementação acadêmica utiliza dados simulados, conforme o README. Essa característica deve ser mantida nos testes e demonstrações.

Para uma futura utilização com dados reais, o grupo deverá:

- Identificar os dados estritamente necessários para cada diagnóstico.
- Evitar enviar ao modelo informações identificáveis que não sejam necessárias.
- Não incluir credenciais em prompts ou registros.
- Definir prazo de retenção e procedimento de eliminação para banco, logs e eventuais cópias.
- Verificar as políticas de retenção do provedor externo.
- Documentar as pessoas autorizadas a acessar os dados.

**LACUNA:** ainda não há evidência suficiente de uma política formal de retenção, descarte, acesso e minimização para todas as etapas do fluxo.

## 7. Avaliação

**Afirmação**

O projeto documenta cenários simulados para avaliar a capacidade do agente de diagnosticar e encaminhar problemas de conexão. Os cenários descritos são:

- **C001:** problema simples que pode ser resolvido com reinicialização.
- **C002:** divergência entre o estado do sistema e o relato do cliente.
- **C004:** falha física que exige encaminhamento para visita técnica.
- **C005:** bairro em manutenção, no qual não deve ser agendada visita individual.
- **C999:** contrato inexistente.

**Evidências**

- `docs/case.md`: descrição dos casos.
- `docs/modelos.md`: análise do modelo e resultados documentados.
- `README.md`: exemplos de execução.
- `logs/`: registros produzidos pelas execuções.

### Resultados e reprodutibilidade

- Quantidade total de casos documentados: cinco identificadores de cenário (`docs/case.md` §2.8) mais 19 casos do golden dataset de avaliação (`exercicios/Avaliação — Agente de Suporte Técnico Doméstico.md`, que cobre comportamento fim a fim incluindo o modelo).
- Quantidade de execuções avaliadas: cinco execuções manuais da Parte 1 (`docs/modelos.md` §3), dez casos reais da Parte 2 com logs em `logs/` (C001, C002, C999, C005, pergunta fora do manual, entrada incompleta, entrada ambígua, escalada para humano e duas execuções de C004 com aprovação editada, mais um log de terminal de C004; 11 logs em `docs/io.md`) e 57 testes automatizados determinísticos (`tests/`), que não dependem do modelo.
- Taxa agregada de sucesso: 57 de 57 nos testes automatizados (`python -m pytest tests -q`). Nos casos reais da Parte 2, os comportamentos esperados apareceram (reinício com reteste, manutenção sem agendar, contrato inexistente sem fonte, recusa pelo portão do RAG, pedido de detalhes sem chamar o modelo, agendamento só depois da aprovação e segunda aprovação sem duplicar a visita). O experimento de `docs/experimento_frase.md` mostra que retirar uma frase do prompt não mudou o comportamento neste caso (N=5). Isso ainda não é uma taxa estatística: é contagem sobre um conjunto pequeno e não repetido.
- Taxa de bloqueio correto de ações proibidas: 100% nos testes automatizados que cobrem ações proibidas (modelo sem a ferramenta de agendar, chamada indevida recusada, rejeitar, expirar e edição inválida sem agendar, proposta sem teste prévio, bairro em manutenção, reinício em falha física).
- Resultados por cenário e por tipo de falha: `tests/test_grafo.py` (caminhos do grafo e guardas), `tests/test_limites_autoridade.py` (ferramentas e banco), `tests/test_rag.py` (recuperação, portão e documento revogado) e `tests/test_memoria.py` (escrita, contradição, decaimento e remoção).
- Versão da suíte de avaliação: cada log de `logs/` grava o hash do commit (campo `commit`) e o modelo; citar esse hash ao reportar qualquer resultado.
- Concordância entre o julgamento do modelo e a avaliação humana: tratado em `exercicios/Avaliação — Agente de Suporte Técnico Doméstico.md`, seção 3 (rubrica do juiz LLM, meta de 85% de concordância) — não é o mesmo assunto desta suíte determinística, que não usa juiz nenhum.
- Testes automatizados de regressão: 57 testes (`python -m pytest tests -q`). Cobrem os limites que não dependem do modelo de linguagem, usando um modelo simulado (`src/llm.py::LLMSimulado`); não substituem os 19 casos do golden dataset da avaliação, que exercitam o modelo.

Os cenários descritos não devem ser tratados como evidência de desempenho estatístico sem um protocolo de avaliação, critérios de sucesso e resultados registrados — o golden dataset de 19 casos é esse protocolo para o comportamento que depende do modelo; esta suíte é o equivalente para o que não depende.

### Plano de avaliação

Para sustentar as afirmações do model card, devem ser realizados testes que verifiquem:

1. Resolução correta do caso C001. — coberto pela execução real `logs/caso_C001_feliz.json` e, no grafo, por `tests/test_grafo.py::test_caminho_feliz_reinicia_e_confirma`.
2. Tratamento da divergência no caso C002. — execução real `logs/caso_C002_divergencia.json`; não automatizado porque depende do modelo.
3. Encaminhamento adequado do caso C004. — execuções reais `logs/caso_C004_pausa_edita.json` e `logs/caso_C004_terminal.json`; automatizado nos quatro desfechos da aprovação em `tests/test_grafo.py`.
4. Bloqueio do agendamento individual no caso C005. — **automatizado**: `tests/test_limites_autoridade.py::test_nao_agenda_em_bairro_em_manutencao` e `tests/test_grafo.py::test_bairro_em_manutencao_nao_chega_na_aprovacao`.
5. Recusa ou tratamento correto do contrato inexistente no caso C999. — **automatizado**: `tests/test_limites_autoridade.py::test_contrato_inexistente_e_erro_como_dado` e `test_agendar_contrato_inexistente`; execução real em `logs/caso_C999_inexistente.json`.
6. Bloqueio de agendamento sem confirmação válida. — **automatizado**, de forma estrutural: `test_modelo_nao_tem_ferramenta_que_agenda`, `test_modelo_chamando_agendar_por_fora_nao_agenda`, `test_rejeitar_nao_agenda`, `test_expirar_nao_agenda_e_encaminha_humano` e `test_edicao_invalida_vira_rejeicao`.
7. Encerramento após o limite de voltas. — **automatizado**: `tests/test_grafo.py::test_limite_de_voltas` (com o limite reduzido para 2 por simulação do modelo).
8. Erro de ferramenta ou indisponibilidade do provedor. — erro de ferramenta automatizado (item 5); erro fatal do modelo automatizado (`test_erro_fatal_do_modelo_encaminha_humano`). **LACUNA:** as tentativas automáticas diante de limite de taxa, conexão e timeout (`src/llm.py`) não têm teste, porque exigem simular a biblioteca `openai`.

Cada teste automatizado registra a entrada utilizada e o resultado esperado no próprio código; `python -m pytest tests -q` mostra o resultado observado e o status de aprovação ou falha.

## 8. Limites conhecidos

**Afirmação**

O agente depende da interpretação de um modelo de linguagem e dos resultados fornecidos pelas ferramentas. Portanto, pode produzir respostas incorretas, interpretar ambiguamente a mensagem do usuário ou selecionar uma ferramenta inadequada.

**Limites identificados ou a investigar**

- Dependência do modelo de linguagem para interpretar a solicitação e escolher ações.
- Possibilidade de respostas incorretas ou inconsistentes.
- Necessidade de encaminhamento humano para solicitações fora do escopo.
- Limitação dos dados e cenários simulados, que não representam toda a variedade de problemas reais.
- Dependência da disponibilidade do provedor e das ferramentas.
- Necessidade de validar entradas e resultados antes de executar operações com efeitos relevantes.

**Evidências**

- `src/agent.py`: fluxo de execução e interação com o modelo.
- `src/tools.py`: ferramentas e validações.
- `src/prompts/suporte_v2.md`: instruções do agente.
- `docs/case.md`: cenários considerados.

**LACUNA:** não há evidência suficiente de uma avaliação abrangente de alucinações, entradas maliciosas, falhas de integração, indisponibilidade do provedor ou tentativas de contornar as regras de negócio. Esses casos precisam ser testados antes de qualquer utilização em produção.

## 9. Riscos aceitos

Um risco só deve ser considerado aceito quando o grupo registra a decisão, a justificativa, o responsável e os controles existentes. A existência de uma lacuna não significa que o risco foi formalmente aceito.

| Risco | Justificativa e controle existente | Decisão |
|---|---|---|
| Respostas incorretas do modelo | O sistema é um protótipo acadêmico e trabalha com cenários simulados. A saída deve ser conferida nos testes. | Aceitação limitada ao ambiente de demonstração, sujeita à confirmação pelo grupo. |
| Interpretação incorreta da mensagem | O agente utiliza um modelo de linguagem para interpretar a solicitação. | Risco conhecido; registrar a necessidade de testes de entradas ambíguas. |
| Execução inadequada de uma ferramenta | As ferramentas de `src/tools.py` e o grafo têm testes automatizados (`tests/`) cobrindo contrato inexistente, bairro em manutenção, falha física, limites de uso, laço e a ausência da ferramenta de agendar no alcance do modelo. | Controlado para os limites testados; falta teste das tentativas automáticas contra indisponibilidade do provedor (§7, item 8). |
| Exposição de dados enviados ao provedor | `docs/modelos.md` §5 e `exercicios/model-card.md` §6.2/§6.3 documentam, por inspeção do código, exatamente quais campos chegam ao modelo (contrato, bairro, mensagem do cliente, resultado dos testes) e quais nunca chegam (nome, MAC do modem). Dados simulados nesta entrega. | Aceito para dados simulados. Para dados reais, ativar Zero Data Retention na Groq deixa de ser opcional. |
| Uso indevido de credenciais ou gastos excessivos | Conta do tier gratuito, sem cartão cadastrado — sem caminho para cobrança (`docs/modelos.md` §5). `.gitignore` agora impede commitar `.env`. | Aceito, condicionado à checagem manual de um minuto (confirmar ausência de cartão em Settings → Billing) que ainda não foi feita por ninguém do grupo. |
| Ausência de revisão humana em decisões críticas | A visita técnica só é agendada depois de uma pausa com aprovação (`interrupt`), com rejeição, edição validada e prazo de 900 s (`docs/humano.md`). | Controlado para a visita técnica. Em aberto: quem responde na operação real (L11). |

**Responsável pela aceitação formal dos riscos:** LACUNA — identificar os integrantes responsáveis e registrar a aprovação no repositório.

Até que essas decisões sejam registradas, a aceitação de riscos permanece restrita à finalidade acadêmica e aos dados simulados do projeto.

## 10. Supervisão humana

**Afirmação**

O grafo encaminha para atendimento humano as solicitações de cobrança, fatura, cancelamento ou pedido de atendente, e pede detalhes quando a mensagem não descreve um problema de conexão (nó `triagem`, sem chamar o modelo). Termina com transbordo quando um limite do orçamento é atingido (`docs/grafo.md` §5). A visita técnica exige aprovação humana pelo nó `aprovacao` (`docs/humano.md`).

**Evidências**

- `src/grafo.py`: nós `triagem`, `aprovacao`, `agendar` e `encaminhar_humano`.
- `docs/humano.md` e `docs/grafo.md`: desenho e taxonomia de términos.
- `tests/test_grafo.py`: comportamento de cada caminho.

### Regras de supervisão

- **Solicitações fora do escopo:** encaminhar para atendimento humano (triagem por palavras-chave, sem chamar o modelo). Pedido de cobrança sem essas palavras chega ao agente, e o prompt e a política P02 ainda o desviam.
- **Mensagem sem sintoma de conexão** (por exemplo, "oi"): a triagem, em código, devolve um pedido de detalhes e termina com `entrada_incompleta`, sem chamar o modelo e sem escalar. Uma regra só no prompt foi tentada antes e o modelo a ignorou.
- **Atendimento sem solução:** encerrar o fluxo e encaminhar quando passar de 6 voltas, 8 chamadas de ferramenta, 12000 tokens ou 120 s, ou quando o mesmo pedido de ferramenta se repetir sem mudança.
- **Agendamento de visita:** só depois da aprovação humana; o modelo não tem a ferramenta que agenda.
- **Falha de ferramenta ou violação de limite:** interromper a ação e impedir a continuidade insegura.

**LACUNAS**

- Não foi definido um responsável nominal pelas aprovações e pelas escaladas na operação real.
- O prazo de 900 s vale para a aprovação do cliente; não há prazo de resposta definido para o atendente humano que recebe a escalada.
- Não há procedimento comprovado para suspender o agente durante uma execução.

A correção proposta é definir responsáveis e prazos para a escalada e o procedimento de suspensão.

## 11. Registros de execução

**Afirmação**

O README descreve arquivos de registro em `logs/` (`caso_<contrato>.json`, ou o rótulo dado por `--rotulo`). Esses registros podem conter a trajetória da execução, chamadas de ferramentas, argumentos, resultados e a resposta final apresentada ao cliente.

**Evidências**

- `README.md`: descrição dos arquivos de log e exemplo de execução.
- `src/agent.py`: implementação do registro de execução (`executar_atendimento`), com o campo `prompts` (arquivo e hash de cada prompt em uso).
- `logs/`: registros gerados durante as execuções.

### Inventário dos registros

| Elemento | Situação documentada | Pendência |
|---|---|---|
| Identificador do caso | O nome do arquivo contém o identificador do contrato simulado. | Confirmado por inspeção do código (§6.2): nenhum outro identificador pessoal (nome, MAC) entra no log, porque nenhuma ferramenta os retorna. |
| Ferramentas chamadas | A trajetória das ferramentas é registrada. | Confirmado: `src/agent.py::executar_atendimento` grava a `trajetoria` do estado do grafo, com `nome`, `args` e `resultado` de cada chamada. |
| Argumentos e resultados | O README informa que são registrados. | Confirmado (§6.2/§6.3): podem conter a mensagem do cliente, o contrato, o bairro e o resultado do teste de linha — nunca nome ou MAC. |
| Resposta final | Registrada. | Confirmado: campo `saida` (`resultado`, `fontes`, `suficiente`, `motivo_parada`), igual ao texto mostrado ao cliente. |
| Versão do modelo e do código | Gravada em cada registro. | Confirmado: os campos `modelo`, `temperature`, `prompts` e `commit` (hash curto do Git; vale `sem-git` quando a pasta não é um repositório) são gravados em cada execução. |
| Prazo de retenção | Não comprovado. | **Corrigido:** 30 dias, aplicado por `scripts/limpar_logs_antigos.py` (`python3 -m scripts.limpar_logs_antigos`), com `--simular` para conferir antes de apagar. Justificativa do prazo em `docs/modelos.md` §5. |
| Controle de acesso | Não comprovado. | Documentado: o acesso aos logs é o mesmo acesso de leitura ao repositório Git — não existe controle adicional. Aceitável enquanto o dado for simulado; para dados reais, precisaria de um repositório ou pasta com controle de acesso próprio. |
| Proteção contra alteração ou exclusão indevida | Não comprovada. | Ainda **LACUNA** — os logs ficam no sistema de arquivos sem controle de integridade (hash, assinatura) nem backup; qualquer um com acesso de escrita ao repositório pode alterá-los sem deixar rastro além do próprio histórico do Git. |

Com as correções, a política de retenção e o conteúdo exato dos logs estão comprovados por inspeção do código; o que resta é integridade e backup, registrado como lacuna residual.

## 12. Histórico de mudanças

**Afirmação**

O projeto é versionado no GitHub e possui histórico de commits. Esse histórico permite consultar mudanças realizadas no código e na documentação.

**Evidências**

- Repositório: https://github.com/MariaCoelhoM/Agente_de_llm
- Histórico de commits: https://github.com/MariaCoelhoM/Agente_de_llm/commits/main
- Arquivos relevantes: `src/agent.py`, `src/tools.py`, `src/db.py`, `src/prompts/suporte_v2.md` e `docs/`.

### Registro de versões

| Versão | Alterações | Aprovação |
|---|---|---|
| Versão inicial documentada neste model card | Consolidação da finalidade, autoridade, dados, riscos e evidências disponíveis. | LACUNA — registrar quem revisou e aprovou. |
| Versões anteriores do agente | Consultar o histórico de commits do repositório para reconstruir as mudanças relevantes. | LACUNA — identificar os commits que alteraram regras de autoridade e registrar os respectivos responsáveis. |

O histórico de commits não comprova automaticamente que uma mudança passou por revisão ou aprovação formal.

**LACUNA:** não existe, neste documento, uma cronologia completa das versões do sistema, das alterações nos controles e das respectivas aprovações. Para corrigir, registrar uma versão de referência, relacionar os commits relevantes e documentar quem aprovou cada alteração de comportamento ou de autoridade.

## Lacunas

Esta seção reúne as pendências que impedem que um auditor confirme todas as afirmações do documento.

| ID | Lacuna | Correção proposta | Prioridade | Status (desta revisão) |
|---|---|---|---|---|
| L01 | Versão formal e responsáveis pelo sistema não definidos. | Registrar responsáveis, commit avaliado e tag de versão. | Média | aberta — depende de nomes que só o grupo pode fornecer |
| L02 | Confirmação do cliente pode depender da interpretação do modelo. | Tornar a confirmação estrutural: o modelo não tem a ferramenta que agenda e a aprovação é um `interrupt` respondido por uma pessoa. | Alta | **fechada** — `src/grafo.py` (nós `aprovacao` e `agendar`), testada em `tests/test_grafo.py` |
| L03 | Privilégios da credencial não comprovados. | Auditar permissões e restringir a chave aos recursos necessários. | Alta | **fechada como característica do provedor** — Groq não oferece escopo granular no tier gratuito (`docs/modelos.md` §5); nada a restringir além do que o provedor permite |
| L04 | Limites de consumo e gastos do provedor não comprovados. | Verificar e documentar cotas, alertas e orçamento. | Alta | **fechada, com uma checagem manual pendente** — sem cartão cadastrado não há caminho para cobrança (`docs/modelos.md` §5); falta só confirmar isso em Settings → Billing |
| L05 | Região, retenção e uso dos dados pelo provedor não comprovados. | Consultar documentação contratual e configuração efetiva do serviço. | Alta | **fechada para região e retenção** (EUA; sem retenção por padrão, até 30 dias se monitoramento de abuso estiver ativo — `docs/modelos.md` §5); uso para treino continua **aberta**, documentação do provedor não responde |
| L06 | Fluxo de dados pessoais não integralmente verificado. | Inspecionar uma execução e mapear entrada, contexto, ferramentas, provedor e logs. | Alta | **fechada** — §6.2/§6.3 mapeiam campo a campo, por inspeção do código; nome e MAC nunca saem do banco |
| L07 | Prazos de retenção e descarte não definidos. | Criar política de retenção e procedimento de eliminação. | Alta | **fechada** — 30 dias, `scripts/limpar_logs_antigos.py` |
| L08 | Controle de acesso aos registros não comprovado. | Definir permissões e verificar os acessos ao diretório de logs. | Alta | **fechada como documentação, não como controle técnico** — acesso aos logs é o mesmo acesso ao repositório Git; nenhum controle adicional existe |
| L09 | Suíte automatizada e resultados agregados não comprovados. | Implementar testes reproduzíveis e publicar os resultados. | Alta | **fechada para os limites de autoridade** — 57 testes em `tests/`, `python -m pytest tests -q`; resultados estatísticos (muitas repetições) continuam fora do escopo desta suíte |
| L10 | Concordância entre avaliação do modelo e avaliação humana não medida. | Definir critérios de avaliação e comparar os julgamentos. | Média | aberta — tratada em `exercicios/Avaliação — Agente de Suporte Técnico Doméstico.md` §3, ainda não executada |
| L11 | Aprovação humana e procedimento de suspensão não formalizados. | Definir responsáveis, prazos, critérios de escalada e mecanismo de interrupção. | Alta | **parcialmente fechada** — a aprovação humana da visita está implementada e testada (`docs/humano.md`); continuam abertos o responsável nominal, o prazo do atendente e o procedimento de suspensão, que dependem de decisão do grupo |
| L12 | Inventário completo de ferramentas e permissões não consolidado. | Revisar cada função, seus efeitos e as permissões realmente necessárias. | Alta | **fechada** — §4, cinco ferramentas inventariadas uma a uma, com leitura/escrita e alcance de cada uma |
| L13 | Histórico de mudanças e aprovações incompleto. | Relacionar versões, commits relevantes e responsáveis pelas aprovações. | Média | aberta — depende de decisão do grupo sobre quem aprova |
| L14 | Testes de falhas, entradas maliciosas e tentativas de contornar controles não comprovados. | Criar testes de segurança e regressão para os limites de autoridade. | Alta | **parcialmente fechada** — contrato inexistente, bairro em manutenção, chamada indevida da ferramenta de agendar, contrato forjado pelo modelo, citação inventada, laço e limites de voltas, ferramentas, tokens e testes estão cobertos; as tentativas automáticas contra indisponibilidade do provedor e o limite de tempo continuam sem teste |

## Conclusão: o agente está dentro de sua autoridade?

A segunda versão fechou as lacunas de confirmação de agendamento, credenciais e gastos, dados pessoais e retenção, e testes automatizados. Esta versão leva o documento ao estado final da Parte 2: a confirmação virou estrutural (o modelo não tem a ferramenta que agenda e a visita depende de uma aprovação humana por `interrupt`), a triagem de entrada incompleta é regra de código, há saída validada com fontes verificadas, RAG com portão de suficiência, memória com remoção por titular verificada por outro programa, e 57 testes. Cada fechamento está amarrado a uma evidência verificável (código, teste, log com hash de commit ou documentação oficial do provedor).

Isso não esgota a auditoria. Continuam abertas lacunas que dependem de decisão do grupo, não de mais inspeção de código: quem são os responsáveis formais (L01), quem aprova mudanças (L13), quem responde às aprovações e escaladas e quem pode suspender o agente e revogar credenciais (L11), o uso de dados para treino pelo provedor, que a documentação pública da Groq não esclarece (L05, parte), a concordância entre o juiz LLM e a avaliação humana, que depende de rodar a suíte de `exercicios/Avaliação — Agente de Suporte Técnico Doméstico.md` (L10), e o teste das tentativas automáticas contra indisponibilidade do provedor e do limite de tempo (L14, parte).

Para as decisões já tomadas e testadas — os limites de autoridade sobre agendamento, contrato inexistente, bairro em manutenção e orçamento do laço — um auditor independente agora consegue reconstruir, a partir do código e dos testes, que o agente respeita esses limites, sem depender de uma leitura favorável do prompt. Para as lacunas que restam, o agente continua sendo tratado como um protótipo acadêmico avaliado com dados simulados, não como um sistema com toda a governança operacional formalizada.
