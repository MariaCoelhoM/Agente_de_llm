# Mudanças desde a Parte 2

Este arquivo é o §0 da Parte 3 e o **histórico de mudanças** que o *model card* cobra (`docs/model-card.md` §12). Cada linha diz o que estava errado ou faltando, o que mudou, e onde. A coluna "Commit" traz o hash que contém a mudança (`git log --oneline -- <arquivo>` confirma). **Limite do que o histórico prova:** antes da devolutiva da Parte 3 o repositório tem um único commit, `5472cdd` ("Agente LLM"), que reúne tudo o que está nas seções 1 a 4. Para essas linhas o hash diz que a mudança existe nesse commit, não quando entrou, e um `git diff` entre versões anteriores não mostra nada útil. As correções da seção 6 já têm um commit cada.

## 1. Correções apontadas na devolutiva da Parte 1 (nota 6,6)

| # | O que estava errado (devolutiva) | O que mudou | Onde | Commit |
|---|---|---|---|---|
| D1 | `requirements.txt` sem `httpx` fixado: `TypeError` na instalação limpa | `httpx==0.27.2` fixado (já na Parte 2) e comentado; todas as dependências novas também fixadas | `requirements.txt` | `5472cdd` |
| D2 | Cinco ferramentas, limite de quatro | `obter_data_atual` saiu; a data de hoje e a de amanhã vão no prompt de sistema, montadas pelo código. **Cinco** ferramentas visíveis ao modelo hoje (a Parte 2 acrescentou `propor_visita` e `consultar_base_conhecimento`, e o limite de 2 a 4 era da Parte 1) | `src/tools.py`, `src/grafo.py` (`_mensagens_para_o_modelo`) | `5472cdd` |
| D3 | Confirmação da escrita preenchida pelo modelo; o "sim" do cliente nunca chegava | Resolvido na Parte 2 com `interrupt`; na Parte 3 o "sim" chega **pelo chat**: o cliente digita e o código interpreta (`interpretar_aprovacao`). O modelo não tem a ferramenta que agenda nem lê a resposta | `src/chat.py`, `docs/humano.md` §2 | `5472cdd` |
| D4 | C002 não isolava a divergência (bairro em manutenção) | Novo contrato **C003**: ONLINE, bairro sem manutenção, cliente diz que caiu. Casos G02/G03 da suíte | `src/db.py`, `docs/case.md` §8 | `5472cdd` |
| D5 | Nenhum log mostrava a escrita executada | Logs da Parte 2 (`logs/parte2/caso_C001_feliz.json`: `reiniciar_conexao`; `caso_C004_pausa_edita.json`: visita agendada) e da Parte 3 (`logs/parte3/`, `evals/resultados/*/casos.jsonl`, campo `visitas`) | `logs/`, `evals/resultados/` | `5472cdd` |
| D6 | `docs/modelos.md` afirmava que o C001 reiniciou, e o log não mostrava | Linha corrigida, com a evidência da Parte 2 e a admissão do erro | `docs/modelos.md` §3 | `5472cdd` |
| D7 | Modelo escolhido (qwen) fora da análise; sem custo do semestre | Qwen3.8 27B nos mesmos eixos, conta com tokens medidos nos logs da Parte 2, custo por mês e do semestre | `docs/modelos.md` §1, §2.1 | `5472cdd` |
| D8 | Três candidatos não rodados | **Continua LACUNA**, agora com o instrumento pronto: a suíte roda qualquer modelo trocando o `.env` | `docs/modelos.md` §3 | `5472cdd` |
| D9 | Contexto sem "antes e depois" | Escrito: de onde vem a entrada (WhatsApp + telefone) e quem consome cada saída | `docs/case.md` §2.1 | `5472cdd` |
| D10 | Verificador "a construir", sem os 10 casos rotulados | Construído: golden dataset com 28 casos | `evals/dataset.jsonl`, `docs/evals.md` | `5472cdd` |
| D11 | O atendente humano chamado não estava na tabela de perfis | Perfil "Atendente humano" acrescentado, com o que ele pode fazer | `docs/case.md` §2.1 | `5472cdd` |
| D12 | Reinício (escrita reversível) não marcado como escrita no workflow | Marcado `[ESCRITA reversível — sem confirmação]`, com o porquê; agendamento e registro também marcados | `docs/case.md` §3 | `5472cdd` |
| D13 | Faltava diagrama de arquitetura com condições de parada | Já existia na Parte 2 (`docs/arquitetura.md` §2); atualizado com a camada de chat e os novos términos | `docs/arquitetura.md` §2, §4.5 | `5472cdd` |
| D14 | Prompt embutido no código; `prompts/suporte_v1.md` não era carregado | Resolvido na Parte 2 (`src/prompts/`); na Parte 3 o v1 foi movido para `src/prompts/` como histórico; a cópia que sobrou em `prompts/` na raiz só foi removida em `9ed2550` | `src/prompts/` | `5472cdd`, `9ed2550` |
| D15 | Pasta `logs ` com espaço, sem `dados/`, sem `.gitignore`, `.env.example` vazio, README sem nomes e com blocos quebrados, arquivos soltos na raiz | `logs_parte1/` → `logs/parte2/` (e `caso_C004_pausa_edita 1.json` sem o " 1"); `gitignore` → `.gitignore`; `.env.example` com os nomes; `docs/grafo 1.md` → `docs/grafo.md`; README reescrito com os integrantes. Sobras que ainda existiam e saíram depois: `gitignore` sem ponto (`9ed2550`), `docs/grafo 1.md` (`be34635`), `logs_parte1/` (`52207be`) | raiz | `5472cdd`, `9ed2550`, `be34635`, `52207be` |
| D16 | Contagem "3 têm decisão do modelo (2, 3, 4 e 8)" | Já corrigida na Parte 2 ("4 têm") | `docs/case.md` §3 | `5472cdd` |
| D17 | `json.loads` dos argumentos sem tratamento | Argumento malformado vira `{}` e o erro é registrado, nos dois pontos (`llm.py` e nó `ferramentas`) | `src/llm.py` (`_args_seguros`), `src/grafo.py` | `5472cdd` |
| D18 | Sem orçamento de tokens | Existia desde a Parte 2 (12.000); na Parte 3 é por turno, mais 60.000 por conversa | `src/guardas.py` | `5472cdd` |

## 2. Defeitos encontrados nesta entrega (não apontados pela correção)

| # | O que estava errado | Como apareceu | O que mudou | Commit |
|---|---|---|---|---|
| E1 | Os testes não rodavam: faltava `tests/__init__.py` e o `from .conftest import` falhava na coleta | rodando `python -m pytest` do zero | `tests/__init__.py` criado; 106 testes passam | `5472cdd` |
| E2 | O detector de laço nunca pegava a **mesma escrita repetida** (reiniciar, reiniciar, reiniciar): a escrita zerava a própria contagem | cenário ASI10 ("reinicie 10 vezes") | `detectar_laco` só para numa escrita **diferente**; teste `test_reinicio_repetido_e_laco` | `5472cdd` |
| E3 | Uma exceção numa ferramenta (ex.: `database is locked`) derrubava o atendimento sem motivo e sem log (ASI08, apontado no exercício da Aula 14) | revisão do exercício 14 | `except Exception` no nó `ferramentas` → motivo `ferramenta_indisponivel` | `5472cdd` |
| E4 | O texto de correção do verificador (C4) dizia "Nenhuma visita técnica foi agendada" e o próprio verificador lia isso como afirmação de agendamento | **a suíte pegou**: caso G25 falhou na rodada `3.0.0-rc1_regras` | "nenhum/nenhuma" entrou na lista de negações; teste `test_c4_texto_corrigido_nao_dispara_o_proprio_verificador`; rodada `3.0.0_regras` passa | `5472cdd` |
| E5 | O README da Parte 2 citava `scripts/demo_remocao.py` e `scripts/limpar_logs_antigos.py`, que não existiam | revisão do README | os dois scripts foram escritos | `5472cdd` |
| E6 | A remoção do titular não alcançava os traces (que passaram a existir) | revisão de cobertura (P2 §5.4) | `remover_titular` apaga os traces das conversas do titular; `varrer_contrato` lê `.jsonl` | `5472cdd` |

## 3. O que entrou na Parte 3

| Mudança | Versão | Onde | Documento | Commit |
|---|---|---|---|---|
| Chatbot de vários turnos sobre o mesmo grafo (`thread_id` por conversa) | 3.0.0 | `src/chat.py` | `docs/arquitetura.md`, `docs/memoria.md` §5 | `5472cdd` |
| Orçamento por turno + teto da conversa; janela de 4 turnos; triagem "sem sintoma" só no 1º turno | 3.0.0 | `src/guardas.py`, `src/grafo.py` | `docs/arquitetura.md` §4.4 | `5472cdd` |
| C1 — identidade pelo canal (telefone → contrato) | 3.0.0 | `src/chat.py` (`resolver_contrato`), `src/db.py` (tabela `canais`) | `docs/seguranca.md` | `5472cdd` |
| C2 — provedor do modelo em lista de permitidos, antes de enviar a chave | 3.0.0 | `src/llm.py` (`validar_base_url`) | `docs/seguranca.md` | `5472cdd` |
| C3 — memória sanitizada (instrução e dado pessoal não persistem); memória delimitada como dado | 3.0.0 | `src/memoria.py` (`sanitizar_relato`), `src/grafo.py` | `docs/seguranca.md`, `docs/memoria.md` §8 | `5472cdd` |
| C4 — verificador de afirmações ("agendei", "resolvido") contra a trajetória | 3.0.0 | `src/grafo.py` (`verificar_afirmacoes`) | `docs/seguranca.md` | `5472cdd` |
| C5 — suspensão do agente (kill switch) | 3.0.0 | `src/guardas.py` (`agente_suspenso`), nó `entrada` | `docs/model-card.md` §3 | `5472cdd` |
| Trace OpenTelemetry GenAI (arquivo + OTLP opcional) | 3.0.0 | `src/observabilidade.py` | `docs/observabilidade.md` | `5472cdd` |
| Suíte de avaliação, juiz, métricas | — | `evals/` | `docs/evals.md` | `5472cdd` |
| Prompt v3 | 3.0.0 | `src/prompts/suporte_v3.md` | `docs/prompts.md` §2 | `5472cdd` |
| Seed: C003, C006, C007, C008 e telefones; `python -m src.db --reset` | 3.0.0 | `src/db.py` | `docs/case.md` §8 | `5472cdd` |
| Modelo de regras (substituto determinístico, sem chave) | — | `src/modelo_regras.py` | `docs/evals.md` §5 | `5472cdd` |

## 4. Versões

| Versão | O que é |
|---|---|
| 2.0.0 | o sistema entregue na Parte 2 (uma mensagem por execução) |
| 2.1.0 | **rótulo da versão anterior nas rodadas da suíte**: o código desta entrega com os controles C1, C3 e C4 desligados (`--versao-anterior`), o que reproduz a 2.0.0 nesses caminhos. Não é um checkout da Parte 2, porque a Parte 2 não tinha chat nem ponto de entrada para a suíte |
| 3.0.0-rc1 | 3.0.0 com o defeito E4 (rodada guardada como evidência do achado) |
| 3.0.0 | esta entrega |

## 5. Frentes opcionais

Nenhuma das três (multiagente, MCP, multimídia) foi usada. O agente de apoio ao técnico de campo (`docs/case.md` §10) continua como evolução; MCP só se pagaria com mais de um agente consumindo as mesmas ferramentas; o case não recebe mídia nesta versão.

## 6. Correções da devolutiva da Parte 3

| # | O que estava errado | O que mudou | Commit |
|---|---|---|---|
| F1 | Juiz de coerência não executado (§1.3): sem `evals/juiz/validacao.json`, sem matriz humano × juiz, sem desacordos lidos; rótulos de um só rotulador | **Aberto.** Depende de rotulagem manual pelo grupo e de chave da Groq; nada foi preenchido por script. Os 20 itens de `evals/juiz/rotulos.jsonl` seguem sem rótulo. Comandos em `docs/evals.md` §3 | — |
| F2 | Nenhuma rodada com o modelo real (§1.4 e §4.3): latência, custo, términos e erro por ferramenta só do modelo de regras | **Aberto.** Precisa de chave e rede. Comando: `python -m evals.rodar --versao 3.0.0 --modelo real --nome 3.0.0_qwen3.8-27b`, commitar a pasta, `python -m evals.metricas`. LACUNA L1 do *model card* mantida | — |
| F3 | Histórico de commits e `mudancas.md` sem nenhum hash | Coluna "Commit" em todas as tabelas; a limitação do histórico de um commit só está declarada na introdução e no *model card* §12 | `git log --oneline -- docs/mudancas.md` |
| F4a | `prompts/suporte_v1.md` na raiz e `gitignore` sem ponto | removidos (`git rm`); a cópia certa continua em `src/prompts/suporte_v1.md` e o `.gitignore` é o completo | `9ed2550` |
| F4b | `docs/grafo 1.md` com linhas de código desatualizadas | removido; vale `docs/grafo.md` | `be34635` |
| F4c | `logs_parte1/` com 11 arquivos duplicando `logs/parte2/` | removido (conteúdo idêntico) | `52207be` |
| F4d | Pasta de rodada duplicada `3.0.0_regras_20261112-223050` | removida; a rodada oficial é `evals/resultados/3.0.0_regras/` | `e26b3d3` |
| F4e | 3 PDFs em `exercicios/`, e o enunciado pede só Markdown | convertidos para `.md` (texto puro, tabelas reconstruídas) e PDFs removidos; `docs/fontes.md` e `docs/memoria.md` apontam para os `.md` | `44a8fb1` |

**Sobre `commit: "sem-git"` nos `meta.json`.** As rodadas `2.1.0_regras`, `3.0.0-rc1_regras` e `3.0.0_regras` foram executadas fora de um repositório git e gravam `sem-git`. Elas não foram reescritas, porque são a evidência de como a rodada saiu. Para ter rodadas rastreáveis, rodar `python -m evals.rodar` de novo **depois** de commitar o código e commitar a pasta nova: o `meta.json` passa a gravar o hash.

