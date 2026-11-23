# Mudanças desde a Parte 2

Este arquivo é o §0 da Parte 3 e o **histórico de mudanças** que o *model card* cobra (`docs/model-card.md` §12). Cada linha diz o que estava errado ou faltando, o que mudou, e onde. A coluna "commit" fica com o hash do commit que o grupo fizer desta entrega (`git log --oneline -- <arquivo>` mostra qual é).

## 1. Correções apontadas na devolutiva da Parte 1 (nota 6,6)

| # | O que estava errado (devolutiva) | O que mudou | Onde |
|---|---|---|---|
| D1 | `requirements.txt` sem `httpx` fixado: `TypeError` na instalação limpa | `httpx==0.27.2` fixado (já na Parte 2) e comentado; todas as dependências novas também fixadas | `requirements.txt` |
| D2 | Cinco ferramentas, limite de quatro | `obter_data_atual` saiu; a data de hoje e a de amanhã vão no prompt de sistema, montadas pelo código. **Cinco** ferramentas visíveis ao modelo hoje (a Parte 2 acrescentou `propor_visita` e `consultar_base_conhecimento`, e o limite de 2 a 4 era da Parte 1) | `src/tools.py`, `src/grafo.py` (`_mensagens_para_o_modelo`) |
| D3 | Confirmação da escrita preenchida pelo modelo; o "sim" do cliente nunca chegava | Resolvido na Parte 2 com `interrupt`; na Parte 3 o "sim" chega **pelo chat**: o cliente digita e o código interpreta (`interpretar_aprovacao`). O modelo não tem a ferramenta que agenda nem lê a resposta | `src/chat.py`, `docs/humano.md` §2 |
| D4 | C002 não isolava a divergência (bairro em manutenção) | Novo contrato **C003**: ONLINE, bairro sem manutenção, cliente diz que caiu. Casos G02/G03 da suíte | `src/db.py`, `docs/case.md` §8 |
| D5 | Nenhum log mostrava a escrita executada | Logs da Parte 2 (`logs/parte2/caso_C001_feliz.json`: `reiniciar_conexao`; `caso_C004_pausa_edita.json`: visita agendada) e da Parte 3 (`logs/parte3/`, `evals/resultados/*/casos.jsonl`, campo `visitas`) | `logs/`, `evals/resultados/` |
| D6 | `docs/modelos.md` afirmava que o C001 reiniciou, e o log não mostrava | Linha corrigida, com a evidência da Parte 2 e a admissão do erro | `docs/modelos.md` §3 |
| D7 | Modelo escolhido (qwen) fora da análise; sem custo do semestre | Qwen3.8 27B nos mesmos eixos, conta com tokens medidos nos logs da Parte 2, custo por mês e do semestre | `docs/modelos.md` §1, §2.1 |
| D8 | Três candidatos não rodados | **Continua LACUNA**, agora com o instrumento pronto: a suíte roda qualquer modelo trocando o `.env` | `docs/modelos.md` §3 |
| D9 | Contexto sem "antes e depois" | Escrito: de onde vem a entrada (WhatsApp + telefone) e quem consome cada saída | `docs/case.md` §2.1 |
| D10 | Verificador "a construir", sem os 10 casos rotulados | Construído: golden dataset com 28 casos | `evals/dataset.jsonl`, `docs/evals.md` |
| D11 | O atendente humano chamado não estava na tabela de perfis | Perfil "Atendente humano" acrescentado, com o que ele pode fazer | `docs/case.md` §2.1 |
| D12 | Reinício (escrita reversível) não marcado como escrita no workflow | Marcado `[ESCRITA reversível — sem confirmação]`, com o porquê; agendamento e registro também marcados | `docs/case.md` §3 |
| D13 | Faltava diagrama de arquitetura com condições de parada | Já existia na Parte 2 (`docs/arquitetura.md` §2); atualizado com a camada de chat e os novos términos | `docs/arquitetura.md` §2, §4.5 |
| D14 | Prompt embutido no código; `prompts/suporte_v1.md` não era carregado | Resolvido na Parte 2 (`src/prompts/`); na Parte 3 o v1 foi movido para `src/prompts/` como histórico e a pasta `prompts/` da raiz deixou de existir | `src/prompts/` |
| D15 | Pasta `logs ` com espaço, sem `dados/`, sem `.gitignore`, `.env.example` vazio, README sem nomes e com blocos quebrados, arquivos soltos na raiz | `logs_parte1/` → `logs/parte2/` (e `caso_C004_pausa_edita 1.json` sem o " 1"); `gitignore` → `.gitignore`; `.env.example` com os nomes; `docs/grafo 1.md` → `docs/grafo.md`; README reescrito com os integrantes | raiz |
| D16 | Contagem "3 têm decisão do modelo (2, 3, 4 e 8)" | Já corrigida na Parte 2 ("4 têm") | `docs/case.md` §3 |
| D17 | `json.loads` dos argumentos sem tratamento | Argumento malformado vira `{}` e o erro é registrado, nos dois pontos (`llm.py` e nó `ferramentas`) | `src/llm.py` (`_args_seguros`), `src/grafo.py` |
| D18 | Sem orçamento de tokens | Existia desde a Parte 2 (12.000); na Parte 3 é por turno, mais 60.000 por conversa | `src/guardas.py` |

## 2. Defeitos encontrados nesta entrega (não apontados pela correção)

| # | O que estava errado | Como apareceu | O que mudou |
|---|---|---|---|
| E1 | Os testes não rodavam: faltava `tests/__init__.py` e o `from .conftest import` falhava na coleta | rodando `python -m pytest` do zero | `tests/__init__.py` criado; 106 testes passam |
| E2 | O detector de laço nunca pegava a **mesma escrita repetida** (reiniciar, reiniciar, reiniciar): a escrita zerava a própria contagem | cenário ASI10 ("reinicie 10 vezes") | `detectar_laco` só para numa escrita **diferente**; teste `test_reinicio_repetido_e_laco` |
| E3 | Uma exceção numa ferramenta (ex.: `database is locked`) derrubava o atendimento sem motivo e sem log (ASI08, apontado no exercício da Aula 14) | revisão do exercício 14 | `except Exception` no nó `ferramentas` → motivo `ferramenta_indisponivel` |
| E4 | O texto de correção do verificador (C4) dizia "Nenhuma visita técnica foi agendada" e o próprio verificador lia isso como afirmação de agendamento | **a suíte pegou**: caso G25 falhou na rodada `3.0.0-rc1_regras` | "nenhum/nenhuma" entrou na lista de negações; teste `test_c4_texto_corrigido_nao_dispara_o_proprio_verificador`; rodada `3.0.0_regras` passa |
| E5 | O README da Parte 2 citava `scripts/demo_remocao.py` e `scripts/limpar_logs_antigos.py`, que não existiam | revisão do README | os dois scripts foram escritos |
| E6 | A remoção do titular não alcançava os traces (que passaram a existir) | revisão de cobertura (P2 §5.4) | `remover_titular` apaga os traces das conversas do titular; `varrer_contrato` lê `.jsonl` |

## 3. O que entrou na Parte 3

| Mudança | Versão | Onde | Documento |
|---|---|---|---|
| Chatbot de vários turnos sobre o mesmo grafo (`thread_id` por conversa) | 3.0.0 | `src/chat.py` | `docs/arquitetura.md`, `docs/memoria.md` §5 |
| Orçamento por turno + teto da conversa; janela de 4 turnos; triagem "sem sintoma" só no 1º turno | 3.0.0 | `src/guardas.py`, `src/grafo.py` | `docs/arquitetura.md` §4.4 |
| C1 — identidade pelo canal (telefone → contrato) | 3.0.0 | `src/chat.py` (`resolver_contrato`), `src/db.py` (tabela `canais`) | `docs/seguranca.md` |
| C2 — provedor do modelo em lista de permitidos, antes de enviar a chave | 3.0.0 | `src/llm.py` (`validar_base_url`) | `docs/seguranca.md` |
| C3 — memória sanitizada (instrução e dado pessoal não persistem); memória delimitada como dado | 3.0.0 | `src/memoria.py` (`sanitizar_relato`), `src/grafo.py` | `docs/seguranca.md`, `docs/memoria.md` §8 |
| C4 — verificador de afirmações ("agendei", "resolvido") contra a trajetória | 3.0.0 | `src/grafo.py` (`verificar_afirmacoes`) | `docs/seguranca.md` |
| C5 — suspensão do agente (kill switch) | 3.0.0 | `src/guardas.py` (`agente_suspenso`), nó `entrada` | `docs/model-card.md` §3 |
| Trace OpenTelemetry GenAI (arquivo + OTLP opcional) | 3.0.0 | `src/observabilidade.py` | `docs/observabilidade.md` |
| Suíte de avaliação, juiz, métricas | — | `evals/` | `docs/evals.md` |
| Prompt v3 | 3.0.0 | `src/prompts/suporte_v3.md` | `docs/prompts.md` §2 |
| Seed: C003, C006, C007, C008 e telefones; `python -m src.db --reset` | 3.0.0 | `src/db.py` | `docs/case.md` §8 |
| Modelo de regras (substituto determinístico, sem chave) | — | `src/modelo_regras.py` | `docs/evals.md` §5 |

## 4. Versões

| Versão | O que é |
|---|---|
| 2.0.0 | o sistema entregue na Parte 2 (uma mensagem por execução) |
| 2.1.0 | **rótulo da versão anterior nas rodadas da suíte**: o código desta entrega com os controles C1, C3 e C4 desligados (`--versao-anterior`), o que reproduz a 2.0.0 nesses caminhos. Não é um checkout da Parte 2, porque a Parte 2 não tinha chat nem ponto de entrada para a suíte |
| 3.0.0-rc1 | 3.0.0 com o defeito E4 (rodada guardada como evidência do achado) |
| 3.0.0 | esta entrega |

## 5. Frentes opcionais

Nenhuma das três (multiagente, MCP, multimídia) foi usada. O agente de apoio ao técnico de campo (`docs/case.md` §10) continua como evolução; MCP só se pagaria com mais de um agente consumindo as mesmas ferramentas; o case não recebe mídia nesta versão.
