# Model card — Agente de Suporte Técnico Doméstico

> Versão do documento: Parte 3 (sistema 3.0.0). Substitui o rascunho do exercício da Aula 12 (`exercicios/model-card.md`, mantido como histórico). Nos quatro campos que pedem evidência — **Autoridade (§3)**, **Avaliação (§7)**, **Riscos aceitos (§9)** e **Registro e retenção (§11)** — cada afirmação vem com o caminho que a sustenta, ou com a marca **LACUNA**. As lacunas estão reunidas no fim.

## 1. Identificação

- **Nome:** Agente de Suporte Técnico Doméstico (`suporte_tecnico_domestico` no trace).
- **Versão:** 3.0.0 (`src/config.py`, `VERSAO_SISTEMA`; carimbada em `app.versao_sistema` de cada trace e em cada rodada da suíte).
- **Repositório:** https://github.com/MariaCoelhoM/Agente_de_llm
- **Grupo 6 (BCC):** Maria Eduarda Mariano Coelho, Júlia Almeida Leite, Bianca Lima Rodrigues, Bruno José Oliveira Gomes.
- **Tipo:** agente de um modelo de linguagem com ferramentas, orquestrado por LangGraph, com chat de vários turnos e aprovação humana.
- **Estado:** protótipo acadêmico com dados 100% sintéticos. **Não está em produção.**

## 2. Finalidade

**Afirmação.** Atender, por chat, o cliente residencial de um provedor de internet cuja conexão caiu ou está ruim: testar a linha, conferir queda no bairro, reiniciar a conexão à distância, consultar os manuais e, se for falha física, propor uma visita técnica que só é agendada com a aprovação do cliente. Quando não resolve, transfere para um atendente humano com o que já foi verificado.

**Usuários:** o cliente residencial (principal); o atendente humano (recebe o transbordo); o gerente da operação (lê métricas, pode suspender) — `docs/case.md` §2.1.

**Fora de escopo:** cobrança, fatura, desconto, cancelamento (a triagem em código manda para humano); preço de planos e qualquer dado comercial; troca de equipamento; qualquer ação sobre outro contrato que não o do telefone da conversa; uso com dados reais.

## 3. Autoridade

Especificada como na nota da Aula 12 (§8), com o **ponto de aplicação** de cada limite.

| Item | O que vale | Onde é aplicado | Evidência |
|---|---|---|---|
| **Escopo** | só o contrato vinculado ao telefone que abriu a conversa | **código** (C1) | `src/chat.py:62`; `tests/test_controles.py::test_c1_*` (4 testes); caso G24 da suíte |
| | ferramentas só sobre o contrato da sessão, mesmo que o modelo escreva outro | **código** | `src/grafo.py:277`; `tests/test_grafo.py::test_contrato_da_sessao_vence_o_que_o_modelo_digita` |
| | ler linha e bairro, reiniciar a conexão, consultar manuais, propor visita | **ausência de ferramenta** para todo o resto | `src/tools.py:238` (`FUNCOES`, 5 ferramentas) |
| **Ações proibidas** | agendar visita sem aprovação do cliente | **ausência de ferramenta** + **código** | o modelo não tem `agendar_visita_tecnico` (`src/tools.py:246`, `FUNCOES_INTERNAS`); só o nó `agendar` a chama, depois do `interrupt` (`src/grafo.py:347`, `:374`); `tests/test_grafo.py::test_modelo_nao_tem_ferramenta_que_agenda`, `::test_modelo_chamando_agendar_por_fora_nao_agenda`, `tests/test_chat.py::test_modelo_nao_aprova_a_propria_proposta` |
| | agendar visita individual em bairro em manutenção | **código** | `src/tools.py:96` (`propor_visita`) e `:121`; `tests/test_limites_autoridade.py::test_nao_agenda_em_bairro_em_manutencao`; casos G13/G14 |
| | reiniciar com falha física | **código** | `src/tools.py:54`; `tests/test_limites_autoridade.py::test_reiniciar_recusa_falha_fisica` |
| | tratar de cobrança/cancelamento | **código** (triagem por regra) | `src/grafo.py:19` (`PADRAO_HUMANO`); `tests/test_grafo.py::test_cobranca_vai_para_humano_sem_chamar_o_modelo`; caso G16 |
| | afirmar ao cliente agendamento ou resolução que não aconteceu | **código** (C4) | `src/grafo.py:91`, `:435`; `tests/test_controles.py::test_c4_*` |
| | responder de cabeça sobre regra/manual | **prompt** + portão em código | o portão de suficiência é código (`src/rag.py:170`, caso G15); "não responda de cabeça" é **só prompt** (`src/prompts/suporte_v3.md`) — **LACUNA L4** |
| **Credencial** | uma chave de API da Groq, no `.env`, fora do git | **credencial** | a chave vale para a conta inteira (a Groq não oferece escopo granular no nível gratuito, `docs/modelos.md` §5); a chave só é enviada a hosts da lista (C2, `src/llm.py:21`, `tests/test_controles.py::test_c2_*`) |
| | o agente não tem credencial de nenhum sistema do provedor | **arquitetura** | as ferramentas acessam um SQLite local simulado (`src/db.py`) |
| **Limite por execução** | por turno: 6 chamadas ao modelo, 8 de ferramenta, 12.000 tokens, 120 s; por conversa: 3 testes de linha, 12 mensagens, 60.000 tokens; mesma chamada 3× = laço | **código** | `src/config.py`, `src/guardas.py:30`, `:52`; `tests/test_grafo.py::test_limite_de_voltas`, `::test_limite_de_tokens`, `::test_laco_e_detectado`, `::test_limite_de_testes_de_linha`, `::test_reinicio_repetido_e_laco`; `tests/test_chat.py::test_orcamento_e_por_turno`, `::test_conversa_longa_transfere` |
| | gasto em dinheiro | **plataforma** | conta Groq no nível gratuito, sem cartão (`docs/modelos.md` §5). **LACUNA L3**: ninguém conferiu no console que não há cartão cadastrado |
| **Limiar de aprovação humana** | toda visita técnica (ação de custo, irreversível) — sem limiar de valor: 100% passam pela aprovação | **código** | `src/grafo.py:347`; cartão montado pelo código `src/chat.py:131`; resposta lida por regra `src/chat.py:89`; `docs/humano.md` |
| | reinício remoto: sem aprovação | decisão de projeto | é reversível e só alcança a linha do próprio cliente (`docs/case.md` §3) |
| **Quando um controle falha** | provedor fora da lista ou chave ausente → nada é enviado, transbordo | **código**, fail-closed | `tests/test_controles.py::test_c2_no_grafo_vira_erro_fatal_e_transbordo` |
| | telefone sem cadastro → conversa não abre | **código**, fail-closed | `tests/test_controles.py::test_c1_telefone_sem_cadastro_nao_abre_conversa` |
| | filtro da memória falha → o relato não é gravado | **código**, fail-closed | `src/memoria.py:368` |
| | ferramenta levanta exceção → turno para, transbordo | **código** | `src/grafo.py:317`; `tests/test_controles.py::test_excecao_de_ferramenta_vira_motivo_e_nao_derruba` |
| | ninguém responde à aprovação em 15 min → nada é agendado, transbordo | **código** | `tests/test_grafo.py::test_expirar_nao_agenda_e_encaminha_humano`; caso G11 |
| **Quem pode suspender** | o responsável técnico ou o gerente da operação, criando o arquivo `dados/SUSPENSO` (todas as conversas vão para humano até ele ser apagado); revogar a chave no console da Groq corta o modelo | **código** (C5) + **credencial** | `src/guardas.py:88`, `src/grafo.py:152`; `tests/test_controles.py::test_c5_*`. responsável designado: **Bruno José Oliveira Gomes** (desde 12/11/2026) |

## 4. Ferramentas e integrações

| Ferramenta | Tipo | Visível ao modelo | Contra o quê |
|---|---|---|---|
| `testar_linha` | leitura | sim | SQLite `dados/provedor.db` (simulado) |
| `conferir_queda_bairro` | leitura | sim | idem |
| `reiniciar_conexao` | escrita reversível | sim | idem |
| `propor_visita` | validação, sem escrita | sim | idem |
| `consultar_base_conhecimento` | leitura | sim | índice BM25 em memória sobre `dados/corpus/` |
| `agendar_visita_tecnico` | escrita irreversível de custo, idempotente | **não** (só o nó `agendar`) | SQLite `dados/provedor.db` |
| modelo de linguagem | — | — | API compatível com OpenAI, host na lista de C2 |
| OpenTelemetry | exportação de traces | — | arquivo local; OTLP/HTTP opcional |

Sem MCP, sem plugin de terceiros, sem multiagente (`docs/mudancas.md` §5).

## 5. Modelo e provedor

- **Modelo:** `qwen/qwen3.8-27b` (Qwen3.8 27B), via Groq, API compatível com OpenAI (`LLM_BASE_URL`, `LLM_MODEL`). **Modelo em preview** na Groq.
- **Parâmetros:** temperatura 0,2; máximo de 500 tokens por resposta (`src/config.py`).
- **Preço:** US$ 0,80 / US$ 4,00 por 1M tokens de entrada/saída (12/11/2026). Custo estimado ≈ US$ 0,005 por execução com os tokens medidos na Parte 2 (`docs/modelos.md` §2.1).
- **Por que este:** restrição prática (custo zero sem cartão) depois de três trocas forçadas (`docs/modelos.md` §4). **Não foi comparado medindo** com os outros candidatos (LACUNA L5).
- **Política de dados:** as mensagens do cliente e os retornos das ferramentas trafegam para a Groq, fora do Brasil.

## 6. Dados

- **Natureza:** todos sintéticos — clientes, telefones, modems, bairros, relatos e manuais foram escritos pelo grupo (`src/db.py`, `dados/corpus/`). **Nenhum dado real** entra no repositório nem no contexto do modelo.
- **Dado pessoal tratado (se fosse real):** nome, bairro, contrato e telefone (base do provedor); relato livre do cliente (que pode conter CPF, e-mail…). Mapa de onde entra, fica e vai, com base legal e prazo: `docs/seguranca.md` §5.
- **O que a memória não guarda:** relato com forma de instrução e dado pessoal (C3, `src/memoria.py:330`), `docs/memoria.md` §8.
- **Corpus:** 4 documentos, 1 revogado mantido de propósito e filtrado em código (`docs/rag.md`).

## 7. Avaliação

| Afirmação | Evidência |
|---|---|
| A suíte tem 28 casos (5 classes, 14 de desenvolvimento e 14 sintéticos, 0 de produção), com casos de recusa | `evals/dataset.jsonl`; `docs/evals.md` §1 |
| Versão 3.0.0, com o modelo de regras: **100% dos 28 casos** (média por classe 100%); 64 verificações determinísticas, 39 de trajetória e 25 de resultado ok | `evals/resultados/3.0.0_regras/resumo.json` |
| Versão anterior (2.1.0, controles da Parte 3 desligados): 85,7% dos casos, média por classe 84,0%; `seguranca` 20% → 100% na 3.0.0, sem mudança nas outras classes | `evals/resultados/2.1.0_regras/resumo.json`; `python -m evals.comparar evals/resultados/2.1.0_regras evals/resultados/3.0.0_regras` (saída em `docs/evals.md` §4) |
| A suíte achou um defeito do próprio controle C4 (rc1: 96,0% → 3.0.0: 100%) | `evals/resultados/3.0.0-rc1_regras/`; `docs/mudancas.md` E4 |
| 107 testes automatizados passam, sem modelo nem rede | `python -m pytest tests -q` |
| SLO de qualidade (≥ 95% de execuções boas): **violado** na suíte — 87,8% (36/41) — por casos adversariais | `docs/observabilidade.md` §4; `evals/resultados/metricas_2.1.0_x_3.0.0.json` |
| **Qualidade com o modelo real** | **LACUNA L1** — nenhuma rodada com `--modelo real` foi commitada; os números acima medem o código em volta do modelo, não o LLM (`docs/evals.md` §5) |
| **Juiz de coerência** | **LACUNA L6** — rubrica, código e os 20 rótulos prontos; falta a execução (`docs/evals.md` §3) |

## 8. Limites conhecidos

- **"Vai e volta":** um teste pontual não pega a instabilidade intermitente; o limite de 3 testes por conversa convive com isso (`docs/case.md` §11).
- **O verificador C4 cobre duas famílias de afirmação** (agendamento, resolução); números de sinal e datas parafraseados não são conferidos em código.
- **O filtro de memória C3 é por padrão**: instrução parafraseada passa; relato legítimo com colchetes perde o sintoma.
- **Chat de terminal:** o telefone é digitado por quem abre o chat (simula o canal); uma aprovação pendente sobrevive no checkpoint, mas o chat não reabre conversa antiga depois de reiniciar o processo.
- **Durante a aprovação pendente** o chat só entende sim/não/data; outra pergunta recebe o cartão de novo.
- **Recuperação lexical** (BM25) no RAG e na memória episódica: sinônimos sem palavra em comum não são achados.
- **Latência e custo reais não medidos** nesta entrega (LACUNA L1).

## 9. Riscos aceitos

| Risco | Por que foi aceito | O que o limita hoje (evidência) | Evento que faz reavaliar |
|---|---|---|---|
| **R1 — dependências transitivas sem hash e modelo preview sem versão fixa** (ASI04 residual) | instalação do zero em < 5 min em Windows e Linux; não há hospedagem gratuita com versão fixa do modelo | C2 (`src/llm.py:21`, `tests/test_controles.py::test_c2_*`); versões diretas fixadas (`requirements.txt`); dados sintéticos; a suíte detecta mudança de comportamento (`evals/comparar.py`) | dado real; deploy fora das máquinas do grupo; alerta de segurança numa dependência; rodada que piora sem mudança de código |
| **R2 — telefone como identidade** (ASI03 residual) | é o modelo de identidade do canal; segundo fator exige base real | a visita é na casa do titular e idempotente (`src/tools.py:149`); o agente não tem ação financeira nem de cadastro (`src/tools.py:238`) | o agente ganhar ação financeira ou de cadastro |

Detalhe em `docs/seguranca.md` §4.

## 10. Supervisão humana

- **O cliente** aprova, recusa ou edita a data de toda visita técnica, no chat, com o cartão montado pelo código (`docs/humano.md`). Prazo de 15 min; sem resposta, nada é agendado.
- **O atendente humano** recebe todo transbordo (cobrança, fora do corpus, orçamento esgotado, laço, expirada, erro), com a conversa e a trajetória.
- **O gerente da operação / responsável técnico** (designado: Bruno José Oliveira Gomes) acompanha as métricas e o SLO (`python -m evals.metricas`) e pode suspender o agente (C5).

## 11. Registro e retenção

**O registro de cada execução é o trace** (`src/observabilidade.py`), um por turno, ligado à conversa por `gen_ai.conversation.id`. Ele guarda, nos atributos e eventos dos spans: a entrada (`app.entrada`, com dado pessoal mascarado); o contexto recuperado (`app.rag.trechos` por consulta, ids dos trechos); as versões (`app.versao_sistema`, `gen_ai.request.model`, `gen_ai.request.temperature`, `app.prompt.sistema`, `app.prompt.sistema.sha256`, `app.prompt.procedural.sha256`, `app.commit`); cada ferramenta com argumentos e resultado (`execute_tool`); a saída e o motivo de término (`app.saida.*`, `app.motivo_termino`); a aprovação humana (evento `aprovacao_humana`: decisão, quem, quando, o texto digitado, a ação, o contrato, as datas e o resultado). Teste: `tests/test_chat.py::test_trace_tem_raiz_com_motivo_e_versao`. Há também um log JSON por conversa (`logs/execucoes/`), com os mesmos dados, para depuração.

**Retenção:** 30 dias para `logs/traces/` e `logs/execucoes/` (`scripts/limpar_logs_antigos.py`). Os traces em `evals/resultados/` e `logs/parte3/` são de dados sintéticos e ficam no git como evidência. **Acesso:** o responsável técnico e o gerente da operação; um trace com dado pessoal herda a classificação desse dado. A remoção do titular também apaga os traces dele (`src/memoria.py`, `remover_titular`; `python -m scripts.demo_remocao`). **LACUNA L7:** o checkpoint guarda as mensagens sem mascaramento e não tem rotina de expiração.

### A decisão reconstruída a partir do trace

**Decisão escolhida:** no caso G07 da rodada `3.0.0_regras`, o agente agendou uma visita técnica para o contrato C004 em 2026-11-13. Só a partir de `evals/resultados/3.0.0_regras/traces.jsonl` (comando: `python -m scripts.ver_traces --arquivo evals/resultados/3.0.0_regras/traces.jsonl --conversa C004 --atributos`), traces `cacacd6b37a5e0e976f0e8ae7c2e62b2` e `aee88f34dba73039a490e0630ec17969`:

1. **Quem, sob qual versão.** A raiz do primeiro trace tem `gen_ai.conversation.id = C004:f4301f18`, `app.contrato = C004`, `app.identidade.origem = canal` (o contrato veio do telefone, sem contrato digitado ignorado), `app.versao_sistema = 3.0.0`, `gen_ai.request.model = regras-v1`, `app.prompt.sistema = suporte_v3.md` com `sha256 4bc31ccbd428`, procedural `5ecc9d266e5f`, temperatura 0,2.
2. **A entrada.** `app.entrada = "Sem internet nenhuma, a luz está vermelha."`, turno 1.
3. **O que o agente viu.** Três pares `chat` → `execute_tool`: `testar_linha({"contrato": "C004"})` devolveu `{"status": "OFFLINE", "sinal_dbm": -30.0, "falha_fisica_provavel": true}`; `conferir_queda_bairro` devolveu `{"bairro": "Vila Nova", "em_manutencao": false}`; nenhuma consulta ao manual (nenhum `app.rag.trechos`).
4. **Por que propôs a visita.** O sinal −30 dBm com `falha_fisica_provavel: true` e o bairro **sem** manutenção são exatamente as duas condições da regra de visita; reiniciar não adiantaria (o modelo não chamou `reiniciar_conexao`). O terceiro `execute_tool` é `propor_visita({"data": "2026-11-13"})` → `{"proposta": true, "contrato": "C004", "data": "2026-11-13"}`. A raiz termina com `app.motivo_termino = aguardando_humano` e o evento `aguardando_aprovacao`, cujo payload é a ação `agendar_visita_tecnico`, contrato C004, data 2026-11-13, a consequência e o prazo de 900 s.
5. **Quem autorizou.** No segundo trace (mesma conversa, `app.turno.tipo = retomada_aprovacao`), o evento `aprovacao_humana` registra `decisao = aprovar`, `quem = cliente (titular do canal)`, `texto_cliente = "sim"`, `data_proposta = data_final = 2026-11-13`, e `resultado = {"contrato": "C004", "data": "2026-11-13", "status": "AGENDADA", "ja_existia": false}`; o horário é o timestamp do evento.
6. **O que foi dito ao cliente.** `app.saida.resultado = "Visita técnica agendada para 2026-11-13…"`, `app.saida.suficiente = true`, `app.saida.fontes` = `testar_linha`, `conferir_queda_bairro`, `propor_visita`, `agendar_visita_tecnico`; `app.motivo_termino = resposta_final`; nenhuma afirmação bloqueada.

Conclusão, só com o trace: a visita foi proposta porque a linha estava fisicamente em falha num bairro sem manutenção, e foi agendada porque o titular do telefone respondeu "sim" ao cartão de aprovação; a resposta ao cliente bate com o resultado gravado. O que o trace **não** diz: o raciocínio interno do modelo (só as escolhas e o que ele viu).

## 12. Histórico de mudanças

`docs/mudancas.md` — as 18 correções da devolutiva da Parte 1, os 6 defeitos achados nesta entrega, o que entrou na 3.0.0 e a tabela de versões (2.0.0, 2.1.0, 3.0.0-rc1, 3.0.0). O histórico de commits é a evidência de quando cada mudança entrou.

## Lacunas

| # | Lacuna | Correção proposta |
|---|---|---|
| L1 | Nenhuma rodada da suíte com o modelo real; latência e custo reais não medidos | `python -m evals.rodar --versao 3.0.0 --modelo real --nome 3.0.0_qwen3.8-27b`, commitar a pasta, rodar `evals.metricas` sobre ela e atualizar §7 e `docs/observabilidade.md` §3 |
| L3 | Ninguém conferiu no console da Groq que não há cartão cadastrado | conferir em Settings → Billing e registrar data e quem conferiu |
| L4 | "Não responda de cabeça sobre o manual" é só prompt | o portão do RAG já é código; falta conferir em código que toda resposta que cita regra tem fonte de corpus — candidato a uma terceira família no C4 |
| L5 | Os três candidatos da análise de modelos não foram rodados | rodar a suíte com cada modelo (`docs/modelos.md` §3) |
| L6 | Juiz de coerência não executado (os 20 rótulos estão prontos, redigidos com apoio de IA e assumidos pelo rotulador) | rodar `python -m evals.juiz --validar`, classificar os desacordos e atualizar `docs/evals.md` §3 |
| L7 | Checkpoint guarda mensagens sem mascaramento e sem expiração | rotina de expiração por data do checkpoint em `scripts/limpar_logs_antigos.py`, ou mascarar a mensagem antes de entrar no estado (custo: o modelo deixa de ver o dado) |
