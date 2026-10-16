# Model Card — Agente de Suporte Técnico Doméstico

> **Status do documento:** versão inicial para auditoria acadêmica.  

Este documento descreve a finalidade, as capacidades, a autoridade, os dados tratados, os riscos e os controles do Agente de Suporte Técnico Doméstico. Cada afirmação verificável deve estar associada a uma evidência consultável no repositório ou em uma configuração externa. Quando não há evidência suficiente, o documento declara explicitamente uma lacuna.

## 1. Identificação

**Afirmação**

O sistema é um agente de inteligência artificial desenvolvido para realizar diagnóstico e suporte técnico doméstico de problemas de conexão à internet. O projeto utiliza um modelo de linguagem para interpretar a solicitação do cliente, selecionar ferramentas e formular uma resposta.

O sistema é desenvolvido em Python e possui código em `src/`, instruções em `prompts/`, documentação em `docs/` e registros de execução em `logs/`.

**Responsáveis**

- Integrantes responsáveis pelo desenvolvimento: LACUNA — inserir os nomes completos dos integrantes do grupo.
- Responsável pela aprovação das mudanças: LACUNA — definir quem revisa e aprova alterações no agente.
- Responsável por suspender o sistema em caso de falha: LACUNA — definir uma pessoa responsável e um procedimento de interrupção.

**Evidências**

- `README.md`: identificação do projeto e instruções de execução.
- `src/agent.py`: implementação principal do agente.
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
- `prompts/suporte_v1.md`: instruções de comportamento do agente.

**LACUNA:** as restrições descritas no prompt não comprovam, isoladamente, que todas as utilizações fora de escopo são bloqueadas tecnicamente. É necessário testar cada restrição e identificar os pontos de aplicação no código.

## 3. Autoridade

### 3.1 Escopo autorizado

O agente pode interpretar a solicitação do usuário, consultar os dados simulados associados ao contrato, executar as ferramentas disponibilizadas pelo projeto, tentar solucionar problemas de conexão e propor um agendamento conforme as regras de negócio implementadas.

O agente não deve realizar operações que não estejam previstas nas ferramentas disponibilizadas nem ultrapassar os limites definidos para cada ferramenta.

**Evidências**

- `src/agent.py`: definição do agente, instruções, ferramentas disponibilizadas e fluxo de execução.
- `src/tools.py`: implementação das ferramentas e validações operacionais.
- `prompts/suporte_v1.md`: regras de comportamento.
- `README.md`: descrição dos cenários e do comportamento esperado.

### 3.2 Matriz de autoridade e ponto de aplicação

| Limite ou controle | Ponto de aplicação | Evidência e situação |
|---|---|---|
| Consultar apenas contratos previstos nos cenários simulados | Código e banco de dados | `src/db.py` e `src/tools.py`. Verificar se a consulta bloqueia contratos inexistentes. |
| Limitar o atendimento a seis mensagens sem solução | Código | `src/agent.py`. O README documenta o limite; associar a um teste automatizado que demonstre o encerramento. |
| Limitar a quantidade de testes de linha | Código | `src/agent.py`. Verificar o contador e testar a tentativa de ultrapassar o limite. |
| Não agendar sem confirmação explícita | Código, prompt e validação da entrada | `src/tools.py` e `prompts/suporte_v1.md`. A validação precisa comprovar a origem da confirmação, não apenas aceitar um valor booleano. |
| Não agendar visita individual durante manutenção no bairro | Código e dados | `src/tools.py` e `src/db.py`. Criar ou localizar teste que demonstre o bloqueio no caso C005. |
| Não realizar operações além das ferramentas permitidas | Ausência de ferramenta e validação no código | `src/agent.py` e `src/tools.py`. Inventariar as ferramentas efetivamente registradas e suas permissões. |
| Limitar gastos com o provedor do modelo | Plataforma | LACUNA — verificar limites de orçamento, alertas e cotas na conta do provedor. |
| Restringir o acesso da credencial | Credencial | LACUNA — comprovar os privilégios da chave utilizada e se ela possui acesso apenas aos recursos necessários. |
| Suspender o agente em caso de comportamento inadequado | Operação e plataforma | LACUNA — documentar procedimento, responsável e forma de revogar credenciais ou interromper a execução. |
| Aprovar operações sensíveis por um humano | Código e procedimento operacional | LACUNA — não considerar uma instrução no prompt como aprovação humana efetiva. |

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

A existência dessas variáveis não comprova os privilégios efetivos da credencial, a região de processamento, o orçamento disponível ou os limites de consumo configurados.

- **Credencial:** LACUNA — verificar o escopo real da chave e restringir seus privilégios.
- **Limite de gasto:** LACUNA — registrar o limite configurado no provedor, ou declarar que não há limite comprovado.
- **Falha de controle:** interromper a execução e impedir novas ações até que a falha seja investigada. A implementação desse comportamento deve ser comprovada por teste.
- **Suspensão:** LACUNA — definir quem pode interromper o processo e revogar a credencial utilizada.

## 4. Ferramentas e integrações

**Afirmação**

O agente utiliza ferramentas Python disponibilizadas pelo próprio projeto e um provedor de modelo de linguagem configurado por variáveis de ambiente. O banco de dados simulado fornece informações necessárias para os cenários de atendimento.

**Inventário**

| Ferramenta ou integração | Finalidade | Permissões e evidências |
|---|---|---|
| Modelo de linguagem | Interpretar a solicitação, orientar o fluxo e formular respostas | `src/agent.py` e `prompts/suporte_v1.md`. Verificar o modelo e o endpoint efetivos. |
| Ferramentas de diagnóstico | Consultar informações e executar testes de conexão | `src/tools.py`. Documentar individualmente os parâmetros, os efeitos e as permissões de cada função. |
| Reinicialização da conexão | Tentar solucionar problemas remotamente | `src/tools.py`. Verificar se a operação altera somente o estado simulado ou produz algum efeito externo. |
| Agendamento de visita | Propor ou registrar uma visita técnica conforme as condições do caso | `src/tools.py`. Verificar se o agendamento é apenas simulado ou se existe integração externa. |
| Banco de dados simulado | Armazenar contratos e informações dos cenários | `src/db.py`. O README informa que o banco é gerado localmente e não é versionado. |
| Registros de execução | Registrar a trajetória das ferramentas e a resposta final | `src/agent.py` e diretório `logs/`. |

**Servidores MCP:** LACUNA — verificar o código e as dependências para confirmar se existe algum servidor MCP configurado. Não foi comprovada a utilização de MCP apenas pela documentação consultada.

**Permissões de escrita e envio a terceiros:** LACUNA — revisar todas as funções e integrações para identificar quais apenas consultam informações, quais modificam dados e quais enviam conteúdo para serviços externos.

## 5. Modelo e provedor

**Afirmação**

O agente utiliza um modelo de linguagem configurado por variáveis de ambiente. O projeto prevê as configurações `LLM_BASE_URL`, `OPENAI_API_KEY` e `LLM_MODEL`, permitindo configurar o endpoint, a credencial e o identificador do modelo.

**Evidências**

- `.env.example`: variáveis esperadas para configurar o acesso ao modelo.
- `src/agent.py`: inicialização e chamadas ao modelo.
- `docs/modelos.md`: análise e escolha do modelo.

**Informações que precisam ser comprovadas**

- Nome exato do provedor efetivamente utilizado: LACUNA.
- Identificador exato e versão datada do modelo: LACUNA.
- Data em que a versão do modelo foi verificada: LACUNA.
- Região geográfica de processamento: LACUNA.
- Política de retenção das entradas e saídas no provedor: LACUNA.
- Condições de uso dos dados para treinamento pelo provedor: LACUNA.
- Existência de limites de consumo e de orçamento: LACUNA.

Não se deve inferir o provedor, a versão ou a localização dos dados somente a partir do nome de uma variável de ambiente. Para preencher essas informações, registrar a configuração real utilizada na execução, consultar a documentação contratual do provedor e preservar a evidência sem expor chaves secretas.

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
| Identificador do contrato | Localizar o registro simulado | Entrada do programa, banco e contexto de execução | Dados sintéticos no ambiente acadêmico. Para dados reais, avaliar a base legal aplicável e definir prazo de retenção. |
| Mensagem do cliente | Entender e classificar o problema | Entrada do programa, contexto enviado ao modelo e possível registro de execução | LACUNA — definir base legal, finalidade específica e prazo, caso sejam utilizadas mensagens reais. |
| Nome do cliente, se presente no cadastro | Identificar o registro simulado | `src/db.py` e contexto recuperado, conforme o fluxo executado | LACUNA — confirmar se o nome é efetivamente enviado ao modelo e definir necessidade e retenção para dados reais. |
| Bairro | Verificar a condição de manutenção e a possibilidade de agendamento | Banco simulado e ferramentas de diagnóstico ou agendamento | LACUNA — avaliar necessidade e prazo para dados reais. |
| Endereço MAC do modem | Identificar o equipamento ou consultar informações técnicas, se utilizado no fluxo | Banco simulado e contexto acessado pelas ferramentas | LACUNA — confirmar o compartilhamento com o modelo e documentar finalidade, base legal e retenção. |
| Resultado dos testes de conexão | Diagnosticar a ocorrência | Retorno das ferramentas e contexto do agente | LACUNA — verificar os campos exatos registrados e definir retenção. |
| Argumentos e resultados das ferramentas | Permitir auditoria da trajetória da execução | `logs/caso_<contrato>.json` | LACUNA — verificar quais dados são gravados e estabelecer prazo e controle de acesso. |
| Resposta final do agente | Informar o resultado do atendimento | Saída do programa e registro de execução | LACUNA — confirmar conteúdo, prazo de guarda e acessos. |
| Credencial de acesso ao provedor | Autenticar as chamadas ao modelo | Variável de ambiente utilizada pelo processo | Não registrar a chave nos logs. Definir procedimento de rotação e revogação; não incluir o valor secreto no model card. |

### 6.3 Fluxo dos dados

1. **Entrada:** o contrato simulado e a descrição do problema são fornecidos ao programa.
2. **Consulta:** o agente utiliza as ferramentas disponíveis para recuperar informações e executar diagnósticos.
3. **Contexto do modelo:** informações da solicitação e resultados das ferramentas podem compor as mensagens enviadas ao provedor.
4. **Execução:** argumentos e resultados das ferramentas são registrados conforme o mecanismo de logging implementado.
5. **Saída:** a resposta final é apresentada ao usuário e pode ser gravada no log.

**Evidências:** `src/agent.py`, `src/tools.py`, `src/db.py` e `logs/`.

**LACUNA:** verificar, por inspeção do código e de uma execução real, quais campos efetivamente chegam ao provedor e quais ficam gravados no arquivo JSON. O fluxo acima representa o percurso esperado, não uma comprovação de que todos os campos são enviados em toda execução.

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

- Quantidade total de casos documentados: cinco identificadores de cenário.
- Quantidade de execuções independentes avaliadas: LACUNA.
- Taxa agregada de sucesso: LACUNA.
- Taxa de bloqueio correto de ações proibidas: LACUNA.
- Resultados por cenário e por tipo de falha: LACUNA — consolidar os resultados a partir de execuções reproduzíveis.
- Versão da suíte de avaliação: LACUNA.
- Concordância entre o julgamento do modelo e a avaliação humana: LACUNA.
- Testes automatizados de regressão: LACUNA — identificar os testes existentes ou implementá-los.

Os cenários descritos não devem ser tratados como evidência de desempenho estatístico sem um protocolo de avaliação, critérios de sucesso e resultados registrados.

### Plano de avaliação

Para sustentar as afirmações do model card, devem ser realizados testes que verifiquem:

1. Resolução correta do caso C001.
2. Tratamento da divergência no caso C002.
3. Encaminhamento adequado do caso C004.
4. Bloqueio do agendamento individual no caso C005.
5. Recusa ou tratamento correto do contrato inexistente no caso C999.
6. Bloqueio de agendamento sem confirmação válida.
7. Encerramento após o limite de mensagens.
8. Comportamento em caso de erro de ferramenta ou indisponibilidade do provedor.

Cada teste deve registrar a entrada utilizada, o resultado esperado, o resultado observado, o status de aprovação ou falha e a versão do código avaliada.

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
- `prompts/suporte_v1.md`: instruções do agente.
- `docs/case.md`: cenários considerados.

**LACUNA:** não há evidência suficiente de uma avaliação abrangente de alucinações, entradas maliciosas, falhas de integração, indisponibilidade do provedor ou tentativas de contornar as regras de negócio. Esses casos precisam ser testados antes de qualquer utilização em produção.

## 9. Riscos aceitos

Um risco só deve ser considerado aceito quando o grupo registra a decisão, a justificativa, o responsável e os controles existentes. A existência de uma lacuna não significa que o risco foi formalmente aceito.

| Risco | Justificativa e controle existente | Decisão |
|---|---|---|
| Respostas incorretas do modelo | O sistema é um protótipo acadêmico e trabalha com cenários simulados. A saída deve ser conferida nos testes. | Aceitação limitada ao ambiente de demonstração, sujeita à confirmação pelo grupo. |
| Interpretação incorreta da mensagem | O agente utiliza um modelo de linguagem para interpretar a solicitação. | Risco conhecido; registrar a necessidade de testes de entradas ambíguas. |
| Execução inadequada de uma ferramenta | As ferramentas estão implementadas em `src/tools.py`, mas cada limite deve ser validado por testes. | LACUNA — não declarar o risco controlado sem evidência. |
| Exposição de dados enviados ao provedor | O modelo pode receber mensagens e contexto recuperado. | LACUNA — verificar dados enviados e política de retenção antes de utilizar dados reais. |
| Uso indevido de credenciais ou gastos excessivos | A aplicação utiliza variáveis de ambiente para configurar o acesso ao provedor. | LACUNA — verificar privilégios, limites de consumo e procedimento de revogação. |
| Ausência de revisão humana em decisões críticas | O fluxo de atendimento pode executar ferramentas automaticamente. | LACUNA — definir quais ações exigem aprovação humana e implementar os controles necessários. |

**Responsável pela aceitação formal dos riscos:** LACUNA — identificar os integrantes responsáveis e registrar a aprovação no repositório.

Até que essas decisões sejam registradas, a aceitação de riscos permanece restrita à finalidade acadêmica e aos dados simulados do projeto.

## 10. Supervisão humana

**Afirmação**

O README informa que solicitações relacionadas a cobrança, fatura ou cancelamento devem ser encaminhadas para atendimento humano e que o atendimento deve terminar com indicação de transbordo quando ultrapassar seis mensagens sem solução.

**Evidências**

- `README.md`: descrição dos limites de atendimento.
- `src/agent.py`: fluxo de mensagens e condição de encerramento.
- `prompts/suporte_v1.md`: instruções de encaminhamento.

### Regras de supervisão

- **Solicitações fora do escopo:** encaminhar para atendimento humano, conforme a regra documentada.
- **Atendimento sem solução após seis mensagens:** encerrar o fluxo e indicar o transbordo.
- **Agendamento de visita:** exigir confirmação válida do cliente e verificar as demais condições antes de executar a operação.
- **Falha de ferramenta ou violação de limite:** interromper a ação e impedir a continuidade insegura.

**LACUNAS**

- Não foi comprovado um mecanismo de aprovação humana em tempo real antes de ações sensíveis.
- Não foi definido um responsável nominal pelo atendimento das escaladas.
- Não há prazo de resposta humana documentado.
- Não há procedimento comprovado para suspender o agente durante uma execução.
- Não foi demonstrado por teste que todas as condições de encaminhamento são respeitadas.

A correção proposta é documentar o fluxo de escalada, definir responsáveis e prazos e implementar testes que demonstrem o comportamento esperado.

## 11. Registro e retenção

**Afirmação**

O README descreve arquivos de registro no formato `logs/caso_<contrato>.json`. Esses registros podem conter a trajetória da execução, chamadas de ferramentas, argumentos, resultados e a resposta final apresentada ao cliente.

**Evidências**

- `README.md`: descrição dos arquivos de log e exemplo de execução.
- `src/agent.py`: implementação do registro de execução.
- `logs/`: registros gerados durante as execuções.

### Inventário dos registros

| Elemento | Situação documentada | Pendência |
|---|---|---|
| Identificador do caso | O nome do arquivo contém o identificador do contrato simulado. | Verificar se há outros identificadores pessoais no conteúdo. |
| Ferramentas chamadas | O README informa que a trajetória das ferramentas é registrada. | Conferir os campos efetivos e sua integridade. |
| Argumentos e resultados | O README informa que são registrados. | Verificar se os argumentos podem conter mensagens ou dados pessoais. |
| Resposta final | O README informa que é registrada. | Verificar se existem filtros para dados desnecessários. |
| Versão do modelo e do código | Não comprovada em cada registro. | Registrar identificadores de versão em cada execução. |
| Prazo de retenção | Não comprovado. | Definir prazo e rotina de eliminação. |
| Controle de acesso | Não comprovado. | Documentar permissões de leitura, escrita e compartilhamento. |
| Proteção contra alteração ou exclusão indevida | Não comprovada. | Avaliar mecanismos de integridade, backup e controle de acesso. |

**LACUNA:** não há evidência suficiente de uma política de retenção e acesso aos logs. A existência de um arquivo de registro não comprova, por si só, que ele é íntegro, completo ou protegido.

Para corrigir, definir os campos registrados, remover dados desnecessários, estabelecer prazo de guarda, limitar acessos e registrar a versão do sistema e do modelo utilizada em cada execução.

## 12. Histórico de mudanças

**Afirmação**

O projeto é versionado no GitHub e possui histórico de commits. Esse histórico permite consultar mudanças realizadas no código e na documentação.

**Evidências**

- Repositório: https://github.com/MariaCoelhoM/Agente_de_llm
- Histórico de commits: https://github.com/MariaCoelhoM/Agente_de_llm/commits/main
- Arquivos relevantes: `src/agent.py`, `src/tools.py`, `src/db.py`, `prompts/suporte_v1.md` e `docs/`.

### Registro de versões

| Versão | Alterações | Aprovação |
|---|---|---|
| Versão inicial documentada neste model card | Consolidação da finalidade, autoridade, dados, riscos e evidências disponíveis. | LACUNA — registrar quem revisou e aprovou. |
| Versões anteriores do agente | Consultar o histórico de commits do repositório para reconstruir as mudanças relevantes. | LACUNA — identificar os commits que alteraram regras de autoridade e registrar os respectivos responsáveis. |

O histórico de commits não comprova automaticamente que uma mudança passou por revisão ou aprovação formal.

**LACUNA:** não existe, neste documento, uma cronologia completa das versões do sistema, das alterações nos controles e das respectivas aprovações. Para corrigir, registrar uma versão de referência, relacionar os commits relevantes e documentar quem aprovou cada alteração de comportamento ou de autoridade.

## Lacunas

Esta seção reúne as pendências que impedem que um auditor confirme todas as afirmações do documento.

| ID | Lacuna | Correção proposta | Prioridade |
|---|---|---|---|
| L01 | Versão formal e responsáveis pelo sistema não definidos. | Registrar responsáveis, commit avaliado e tag de versão. | Média |
| L02 | Confirmação do cliente pode depender da interpretação do modelo. | Validar a confirmação de forma independente antes de permitir o agendamento. | Alta |
| L03 | Privilégios da credencial não comprovados. | Auditar permissões e restringir a chave aos recursos necessários. | Alta |
| L04 | Limites de consumo e gastos do provedor não comprovados. | Verificar e documentar cotas, alertas e orçamento. | Alta |
| L05 | Região, retenção e uso dos dados pelo provedor não comprovados. | Consultar documentação contratual e configuração efetiva do serviço. | Alta |
| L06 | Fluxo de dados pessoais não integralmente verificado. | Inspecionar uma execução e mapear entrada, contexto, ferramentas, provedor e logs. | Alta |
| L07 | Prazos de retenção e descarte não definidos. | Criar política de retenção e procedimento de eliminação. | Alta |
| L08 | Controle de acesso aos registros não comprovado. | Definir permissões e verificar os acessos ao diretório de logs. | Alta |
| L09 | Suíte automatizada e resultados agregados não comprovados. | Implementar testes reproduzíveis e publicar os resultados. | Alta |
| L10 | Concordância entre avaliação do modelo e avaliação humana não medida. | Definir critérios de avaliação e comparar os julgamentos. | Média |
| L11 | Aprovação humana e procedimento de suspensão não formalizados. | Definir responsáveis, prazos, critérios de escalada e mecanismo de interrupção. | Alta |
| L12 | Inventário completo de ferramentas e permissões não consolidado. | Revisar cada função, seus efeitos e as permissões realmente necessárias. | Alta |
| L13 | Histórico de mudanças e aprovações incompleto. | Relacionar versões, commits relevantes e responsáveis pelas aprovações. | Média |
| L14 | Testes de falhas, entradas maliciosas e tentativas de contornar controles não comprovados. | Criar testes de segurança e regressão para os limites de autoridade. | Alta |

## Conclusão: o agente está dentro de sua autoridade?

Com as evidências documentadas até aqui, um auditor consegue compreender a finalidade do agente, identificar os arquivos relevantes, conhecer os cenários simulados e iniciar a investigação de uma execução.

Entretanto, **ainda não é possível garantir que um auditor independente consiga decidir, para qualquer decisão concreta, se o agente permaneceu dentro de sua autoridade**. Para isso, é necessário demonstrar que os limites são aplicados no código ou na plataforma, que os registros permitem reconstruir a decisão e que os testes exercitam os casos permitidos e proibidos.

A principal prioridade é comprovar os controles de agendamento, revisar as credenciais e permissões, mapear o percurso dos dados, definir retenção e produzir testes reproduzíveis.

Até que essas pendências sejam resolvidas, o agente deve ser tratado como um protótipo acadêmico avaliado com dados simulados, e não como um sistema cuja segurança operacional esteja integralmente comprovada.
