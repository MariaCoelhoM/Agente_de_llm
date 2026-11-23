# Agente de Suporte Técnico Doméstico

**Grupo 6 (BCC):** Maria Eduarda Mariano Coelho · Júlia Almeida Leite · Bianca Lima Rodrigues · Bruno José Oliveira Gomes

**O problema em uma frase:** descobrir e resolver, na hora e por chat, por que a internet da casa do cliente caiu ou está ruim, testando a linha automaticamente, sem passar por um atendente humano — e só mandar um técnico com a aprovação do cliente.

O sistema é um **chatbot**: o cliente conversa em texto livre, o agente (um grafo LangGraph com um modelo de linguagem e cinco ferramentas) testa a linha, confere queda no bairro, reinicia a conexão, consulta os manuais e, se for falha física, para e pede a aprovação do cliente antes de agendar a visita. Tudo roda sobre dados **simulados** (SQLite).

## Documentação

| Documento | O que tem |
|---|---|
| [docs/guia-do-codigo.md](docs/guia-do-codigo.md) | **comece por aqui**: tudo o que o código faz, em linguagem simples, e todos os comandos |
| [docs/case.md](docs/case.md) | o case completo (Partes 1 e 2), com as correções da devolutiva |
| [docs/mudancas.md](docs/mudancas.md) | **o que mudou desde a Parte 2**, com as correções da devolutiva da Parte 1 |
| [docs/arquitetura.md](docs/arquitetura.md) · [docs/grafo.md](docs/grafo.md) | diagrama, grafo, estado, padrões, términos |
| [docs/io.md](docs/io.md) · [docs/prompts.md](docs/prompts.md) | contrato de entrada e saída, exemplos reais; plano de prompts |
| [docs/rag.md](docs/rag.md) · [docs/memoria.md](docs/memoria.md) · [docs/humano.md](docs/humano.md) | RAG, memória e conversa, aprovação humana |
| [docs/modelos.md](docs/modelos.md) | análise de modelos e custos |
| [docs/evals.md](docs/evals.md) | **Parte 3** — golden dataset, níveis, juiz, comparação entre versões |
| [docs/model-card.md](docs/model-card.md) | **Parte 3** — os 12 campos, a autoridade, a decisão reconstruída do trace, as lacunas |
| [docs/seguranca.md](docs/seguranca.md) | **Parte 3** — canais, riscos (OWASP agêntico), controles e o que custaram, risco aceito, dados pessoais |
| [docs/observabilidade.md](docs/observabilidade.md) | **Parte 3** — plano, traces OpenTelemetry, métricas por versão, SLO |
| [docs/fontes.md](docs/fontes.md) | fontes consultadas |

## Como rodar (do zero)

Precisa de **Python 3.13** (o 3.14 quebra o `pydantic_core`). Comandos para o PowerShell; no Linux e no macOS troque a ativação por `source .venv/bin/activate` e `copy` por `cp`.

```powershell
git clone https://github.com/MariaCoelhoM/Agente_de_llm.git
cd Agente_de_llm
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python -m src.db --reset
```

Edite o `.env` (ele **nunca** vai para o git). Para a Groq:

```
LLM_BASE_URL=https://api.groq.com/openai/v1
OPENAI_API_KEY=<sua chave da Groq>
LLM_MODEL=qwen/qwen3.8-27b
```

Só hosts da lista `HOSTS_LLM_PERMITIDOS` (`src/config.py`: Groq, Mistral, OpenAI, localhost) recebem a chave; outro endereço é recusado antes de qualquer envio (controle C2, `docs/seguranca.md`).

**Sem chave de API?** Tudo funciona com `--modelo regras`, um substituto determinístico do modelo (não é um LLM; serve para testar o sistema e rodar a suíte sem custo — `docs/evals.md` §5).

## Como usar: o chat

```powershell
python -m src.chat --telefone +5511900000004                  # com o modelo do .env
python -m src.chat --telefone +5511900000004 --modelo regras  # sem chave
```

**O que a pessoa digita:** texto livre, como no WhatsApp ("a luz do modem está vermelha e a internet caiu"). O **telefone** simula o número que o WhatsApp autentica: é ele que define o contrato da conversa — o cliente não digita o contrato, e se digitar outro, é ignorado. Telefones de teste:

| Telefone | Contrato | O caso |
|---|---|---|
| `+5511900000001` | C001 | sinal recuperável: o reinício resolve |
| `+5511900000002` | C002 | linha ONLINE, bairro em manutenção |
| `+5511900000003` | C003 | **divergência**: linha ONLINE, bairro normal, cliente diz que caiu |
| `+5511900000004` | C004 | **falha física** (−30 dBm): precisa de visita técnica |
| `+5511900000005` | C005 | bairro em manutenção: não deve agendar |
| `+5511900000006` / `…007` | C006 / C007 | bordas do limiar: −27,0 dBm (falha) e −26,9 dBm (não) |
| `+5511900000008` | C008 | bairro sem cadastro |

Comandos no chat: `/nova` começa outra conversa, `/sair` encerra. `--debug` mostra o objeto de saída completo a cada resposta.

**O que o sistema faz com aquilo:** cada mensagem é um turno do mesmo atendimento. Uma regra em código separa o que vai para um atendente (cobrança, cancelamento, pedido de humano) e o que ainda não descreve um problema; o resto vai para o agente, que testa a linha, confere o bairro, reinicia à distância quando adianta e, se for falha física, propõe uma visita. Quem agenda é o código, depois do "sim" do cliente.

**O que acontece quando o grafo para e espera alguém.** Ao propor a visita, o grafo pausa (`interrupt`) e o chat mostra um cartão montado pelo código, com a ação exata e a consequência. A próxima mensagem do cliente é lida **por regra**, não pelo modelo: "sim" aprova, "não" recusa, uma data ("dia 20", "20/11", "2026-11-20") aprova editando a data. Algo que a regra não entende repete o cartão (na 3ª vez, conta como recusa); 15 minutos sem resposta, nada é agendado e o caso vai para um atendente. O estado da pausa fica no checkpoint (`dados/checkpoints.db`). Detalhes em [docs/humano.md](docs/humano.md).

**Exemplo** — copiado de `logs/parte3/regras/chat_C004_visita_editada.json` e `chat_C001_feliz.json` (gerados por `python -m scripts.rodar_conversas --modelo regras`, em 12/11/2026, com o **modelo de regras**):

```
[conversa C004:… · contrato C004 (pelo telefone)]
Você:   Sem internet nenhuma, a luz está vermelha.
Agente: Para resolver, preciso da sua autorização para uma visita técnica.
          Ação: agendar visita técnica · contrato C004 · data 2026-11-13
          Consequência: desloca um técnico até a casa do cliente; tem custo e não é desfeito sozinho
        Responda "sim" para aprovar, "não" para recusar, ou diga outra data (de 2026-11-12 até 2026-11-26).
        Prazo para responder: 15 min.
Você:   hmm, quanto custa?
Agente: Não entendi sua resposta. Para resolver, preciso da sua autorização para uma visita técnica. (…)
Você:   não, prefiro 15/11
Agente: Visita técnica agendada para 2026-11-15. O técnico vai até a sua casa nessa data. Posso ajudar em mais alguma coisa?

[conversa C001:… · contrato C001 (pelo telefone)]
Você:   oi
Agente: Olá! Sou o assistente de suporte técnico. Ainda não entendi qual é o problema. Me conte: o que a luz do modem
        mostra (verde, vermelha, piscando ou apagada) e se a falha acontece em todos os aparelhos ou só em um.
Você:   A luz do modem está piscando vermelha e a internet caiu.
Agente: Reiniciei a sua conexão e o novo teste mostra a linha ONLINE, com sinal de -22.0 dBm. Pode verificar se voltou a navegar?
        [motivo: resposta_final · suficiente: True · fontes: ['conferir_queda_bairro', 'reiniciar_conexao', 'testar_linha']]
Você:   obrigado!
Agente: Por nada! Se a internet voltar a dar problema, é só me chamar.
```

**Que saída o sistema devolve, e como ler:** cada resposta é um objeto validado (`src/schemas.py`). A do 2º turno acima, inteira:

```json
{
  "resultado": "Reiniciei a sua conexão e o novo teste mostra a linha ONLINE, com sinal de -22.0 dBm. Pode verificar se voltou a navegar?",
  "fontes": [
    {"tipo": "ferramenta", "id": "conferir_queda_bairro", "detalhe": null},
    {"tipo": "ferramenta", "id": "reiniciar_conexao", "detalhe": null},
    {"tipo": "ferramenta", "id": "testar_linha", "detalhe": null}
  ],
  "suficiente": true,
  "motivo_insuficiencia": null,
  "encaminhar_humano": false,
  "motivo_parada": "resposta_final",
  "citacoes_invalidas": [],
  "afirmacoes_bloqueadas": []
}
```

`resultado` é o que o cliente lê; `fontes` é o que sustenta a resposta (ferramentas que rodaram sem erro, ou trechos do manual realmente recuperados); `suficiente=false` é a recusa (com o motivo); `encaminhar_humano=true` encerra a conversa e transfere para um atendente; `afirmacoes_bloqueadas` não vazio significa que o modelo afirmou algo que não aconteceu ("agendei", "resolvido") e o código trocou o texto (controle C4).

**Com o modelo real** (Parte 2, uma mensagem só, `logs/parte2/caso_C001_feliz.json`, qwen/qwen3.8-27b, commit 8b9fd3d, 19/10/2026): `testar_linha → conferir_queda_bairro → reiniciar_conexao → testar_linha`, resposta "Pronto, a linha voltou a ficar ONLINE e o sinal está estável (-22 dBm)…". As conversas da Parte 3 com o modelo real se geram com `python -m scripts.rodar_conversas --modelo real` (vão para `logs/parte3/real/`).

**O que o sistema não faz:** não trata cobrança, fatura, desconto ou cancelamento (transfere para um atendente); não inventa resposta fora dos manuais (recusa e oferece um atendente); não agenda visita sem o "sim" do cliente nem em bairro em manutenção; não atende outro contrato que não o do telefone; não responde perguntas enquanto espera a aprovação. Se um turno passar de 6 chamadas ao modelo, 8 de ferramenta, 12.000 tokens ou 120 s, ou a conversa passar de 12 mensagens, transfere para um atendente.

A interface de **uma mensagem só** da Parte 2 continua: `python -m src.agent C001 "minha internet caiu"` (com `--decisao aprovar|rejeitar|editar|expirou --data AAAA-MM-DD` para scripts).

## Testes

107 testes, sem modelo e sem rede (grafo, chat, aprovação, RAG, memória, limites e os **controles de segurança** da Parte 3):

```powershell
python -m pytest tests -q
python -m pytest tests/test_controles.py -v     # só os controles C1–C5 (docs/seguranca.md §3)
```

## Como rodar a suíte de avaliação e comparar duas rodadas

```powershell
python -m evals.rodar --versao 3.0.0 --modelo regras                    # sem chave
python -m evals.rodar --versao 3.0.0 --modelo real --nome 3.0.0_qwen    # com o modelo do .env
python -m evals.rodar --versao 2.1.0 --versao-anterior --modelo regras  # controles da Parte 3 desligados
python -m evals.comparar evals/resultados/2.1.0_regras evals/resultados/3.0.0_regras
python -m evals.metricas evals/resultados/2.1.0_regras evals/resultados/3.0.0_regras   # p50/p95, custo, términos, SLO
python -m evals.juiz --validar                                          # juiz x rótulo humano (precisa dos rótulos)
```

Cada rodada vai para `evals/resultados/<rodada>/` (`meta.json`, `casos.jsonl`, `resumo.json`, `traces.jsonl`) e é commitada. Explicação em [docs/evals.md](docs/evals.md).

## Como ver os traces

Todo turno gera um trace OpenTelemetry (spans `invoke_agent`, `chat <modelo>`, `execute_tool <ferramenta>`, convenções GenAI), gravado em `logs/traces/AAAA-MM-DD.jsonl` (ou dentro da pasta da rodada, na suíte).

```powershell
python -m scripts.ver_traces                         # os 5 últimos, como árvore
python -m scripts.ver_traces --conversa C004 --atributos
python -m scripts.ver_traces --arquivo evals/resultados/3.0.0_regras/traces.jsonl --trace cacacd6b
```

Para ver numa interface (opcional), suba um coletor OTLP — por exemplo o Jaeger com `docker run -p 16686:16686 -p 4318:4318 jaegertracing/all-in-one` — e ponha `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318` no `.env`; os traces aparecem em http://localhost:16686 (serviço `suporte_tecnico_domestico`), além do arquivo.

## Outros comandos

```powershell
python conferir_grafo.py                       # nós e arestas do grafo que o sistema executa
python -m scripts.rodar_conversas --modelo regras   # as conversas de demonstração, em logs/parte3/
python -m scripts.gerar_io_chat regras         # acrescenta essas conversas a docs/io.md
python -m scripts.rodar_casos --reset          # os 10 casos da Parte 2 (modelo real), em logs/execucoes/
python -m scripts.medir_rag --k 1 --k 3        # recuperação do RAG
python -m scripts.demo_reducer                 # escrita paralela sem reducer é erro
python -m scripts.demo_idempotencia            # aprovar duas vezes agenda uma vez
python -m scripts.demo_remocao                 # grava, varre, remove o titular e varre de novo
python -m scripts.limpar_logs_antigos --simular   # retenção de 30 dias (logs/execucoes e logs/traces)
```

Para **suspender o agente** (kill switch): crie o arquivo `dados/SUSPENSO`; enquanto ele existir, toda conversa vai para um atendente sem chamar modelo nem ferramenta. Apague para reativar.

## Estrutura

```
src/            o sistema: chat.py (conversa), grafo.py, tools.py, llm.py, memoria.py, rag.py,
                observabilidade.py, modelo_regras.py, guardas.py, config.py, db.py, schemas.py
src/prompts/    os prompts, versionados (suporte_v3.md em uso; v1 e v2 como histórico)
evals/          dataset.jsonl, rodar, comparar, juiz, métricas; resultados/ (uma pasta por rodada)
tests/          testes do sistema e dos controles de segurança
dados/          corpus do RAG; os bancos .db são gerados (fora do git)
logs/parte2/    logs reais da Parte 2 (modelo real)
logs/parte3/    conversas de demonstração da Parte 3, com traces
docs/           toda a documentação
exercicios/     material das aulas (histórico)
```
