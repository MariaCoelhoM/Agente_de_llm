# Base de Conhecimento v1 — Agente de Suporte Técnico Doméstico

## 1. Qual informação especializada o agente precisa, e por que ela não está no modelo

O modelo sabe conversar e sabe redes de computadores em geral (o que é Wi-Fi, o que é fibra óptica, lógica de troubleshooting). O que ele não sabe é **como esta operadora especificamente resolve esses problemas** — e é isso que precisa vir de fora.

| Conhecimento necessário | Por que não vem do modelo |
|---|---|
| Manual de sintomas → diagnóstico (ex.: "luz vermelha piscando" = queda de sinal óptico; "luz vermelha fixa" = falha de energia) | É específico demais: o modelo até arrisca um palpite genérico, mas erra o código de LED exato desta marca de ONT/modem |
| Políticas internas de escalonamento (o robô não pode dar desconto, não pode agendar visita sem "SIM" do cliente, limite de 3 testes / 6 mensagens / 5 min) | É privado: são regras de negócio desta empresa, nunca publicadas em lugar nenhum que o modelo tenha visto |
| Manual de equipamentos e limiares técnicos (ex.: "sinal ≥ -19dBm = ONLINE aceitável") | É específico demais: o número exato do limiar é uma decisão de engenharia da operadora, não um fato de domínio público |
| Padrão de qualidade de instalação (o que a foto da fusão de fibra/conector precisa mostrar para ser aprovada) | É privado e específico: é o critério interno usado pelo Agente de Apoio ao Técnico de Campo para validar a foto |
| Roteiro de frases/tom de atendimento ("Vou testar sua linha aqui no sistema agora mesmo...") | É específico demais: é o estilo de comunicação da marca, não um fato genérico |

**O que o agente precisa e o modelo já sabe (não indexar):** conceitos gerais de redes (o que é DNS, o que é um roteador), boas práticas genéricas de atendimento ao cliente, português coloquial do cliente. Indexar isso seria pagar por contexto que não muda a resposta.

**Um ponto que quase entra na lista errada:** o resultado do teste de linha, o status atual do bairro e o histórico do contrato *parecem* conhecimento especializado, mas não são documento — são **dado vivo**, que muda a cada segundo. Isso não é problema de "onde buscar informação estática", é problema de **chamada de ferramenta/API** (`testar_linha`, `conferir_queda_bairro`, `consultar_historico_atendimento`). Tratar isso como se fosse para indexar seria o erro da pergunta 3.

## 2. Onde esses dados estão, e em que estado

| Fonte | Onde vive | Formato | Dono / frequência de mudança | Acesso |
|---|---|---|---|---|
| Manual de sintomas → diagnóstico | Documento interno da equipe de Suporte Técnico Avançado (hoje provavelmente só na cabeça dos atendentes seniores) | A ser formalizado em Markdown/Word | Equipe de Suporte Técnico Avançado; muda pouco, só quando surge um sintoma novo recorrente | Não existe ainda formalizado — precisa ser escrito por nós a partir de entrevista com o suporte avançado (para o projeto, vamos simular com dados criados por nós) |
| Políticas internas / SLA / limites de segurança | Documento de governança da operação (intranet/Confluence, no mundo real) | Word/HTML | Gerência da Operação; muda raramente (mudança de política é evento raro) | Simulado por nós — já temos o conteúdo core no PDF do case |
| Manual de equipamentos (LEDs, limiares de sinal) | Manual do fabricante da ONT/modem + tabela interna de limiares aceitos | PDF do fabricante + planilha interna | Fabricante do equipamento (manual) / Equipe de Engenharia de Rede (limiares); manual quase não muda, limiares podem mudar por modelo de equipamento | Simulado por nós |
| Padrão de qualidade de instalação (para validação por foto) | Manual de procedimento da equipe de Qualidade Técnica | PDF com fotos-referência | Equipe de Qualidade Técnica; muda pouco | Simulado por nós |
| Histórico de atendimento do cliente | Banco de dados / CRM da operadora | Registros de banco (não é documento) | Sistema de CRM; muda a cada atendimento | Via API simulada (`consultar_historico_atendimento`) — **não é fonte de RAG** |
| Teste de linha, status do bairro | Sistema de rede da operadora | Chamada de API em tempo real | Sistema de monitoramento de rede; muda a todo instante | Via API simulada (`testar_linha`, `conferir_queda_bairro`) — **não é fonte de RAG** |

Nenhuma fonte listada para indexação depende de acesso que não temos: como o projeto usa dados simulados (declarado na Parte 1 do case), o manual de sintomas, o manual de políticas e o manual de equipamentos serão escritos por nós mesmos como documentos de apoio. Nenhuma fonte é PDF escaneado — não há problema de OCR aqui.

## 3. O que vai para o índice — e o que não vai

| Vai para o índice (RAG) | Não vai — é dado vivo / consulta estruturada |
|---|---|
| Manual de sintomas → diagnóstico (~30–50 itens de FAQ) | Resultado do teste de linha (chamada de ferramenta, não busca) |
| Manual de políticas e limites de segurança (~1 documento curto, 5–8 seções) | Status de queda no bairro (chamada de ferramenta) |
| Manual de equipamentos e limiares técnicos (~1 documento, 10–20 itens) | Histórico de atendimento do cliente por `id_chamado` (consulta a banco/API, filtro `==`) |
| Padrão de qualidade de instalação, usado pelo Agente de Apoio ao Técnico (~10–15 itens) | Número do contrato do cliente (consulta a banco, filtro `==`) |
| | Limite de "3 testes por atendimento" ou "6 mensagens" (isso é regra de controle de fluxo do agente, vive no código/prompt, não é busca) |

**Volume estimado:** somando as quatro fontes indexáveis, estamos falando de 4 documentos curtos, algumas dezenas de páginas no total. Cortando por unidade natural (ver pergunta 4), isso dá algo entre **50 e 150 chunks** — ordem de grandeza de dezenas, não milhares.

**Consequência direta da escala:** com esse volume, banco vetorial dedicado é over-engineering. Uma matriz numpy com embeddings e busca por cosseno resolve, exatamente como medido na nota 04 para 28 vetores — nosso caso é maior, mas ainda está longe da escala em que um banco vetorial compensaria a complexidade operacional extra.

## 4. A estratégia de chunking

Os quatro documentos têm estruturas diferentes, então a estratégia é diferente para cada um — forçar um corte único (por exemplo, por número fixo de caracteres em tudo) quebraria o "chunk faz sentido sozinho" no manual de sintomas.

| Documento | Unidade natural | Corte | Chunk faz sentido sozinho? | Metadado do chunk |
|---|---|---|---|---|
| Manual de sintomas → diagnóstico | Item de FAQ (um sintoma relatado + diagnóstico + ação recomendada) | Um chunk por item de FAQ | Sim, desde que herde a categoria do sintoma (ex.: "Categoria: sinal fraco") no início do chunk, para não depender do item anterior | `categoria_sintoma`, `agente_aplicavel: cliente` |
| Políticas internas / SLA / limites de segurança | Seção (ex.: "Limites de segurança", "Regras de escalonamento", "O que o robô nunca faz") | Um chunk por seção | Sim, mas cada chunk herda o título da seção como cabeçalho, senão uma frase como "no máximo 3 vezes" fica sem contexto de a que ela se refere | `secao`, `tipo: politica` |
| Manual de equipamentos e limiares técnicos | Item (um código de LED, ou uma faixa de sinal aceitável) | Um chunk por item, com o nome do equipamento/modelo herdado no cabeçalho | Sim, com o herdado — sem isso, "-19dBm = OK" não diz OK para qual equipamento | `modelo_equipamento`, `agente_aplicavel: técnico de campo` |
| Padrão de qualidade de instalação | Item de critério (um critério de aprovação por tipo de foto: fusão de fibra, conector, etiqueta MAC) | Um chunk por critério | Sim, desde que inclua o tipo de foto a que se refere | `tipo_foto`, `agente_aplicavel: técnico de campo` |

O metadado `agente_aplicavel` é o que permite, na hora da recuperação, restringir a busca ao agente que está perguntando (Agente do Cliente não precisa ver o padrão de qualidade de instalação; o Agente do Técnico de Campo não precisa do roteiro de frases de atendimento ao cliente) — evitando trazer contexto irrelevante para o prompt.
