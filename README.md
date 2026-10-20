# Agente de Suporte Técnico Doméstico

## O problema em uma frase
Descobrir e resolver o motivo de a internet da casa do cliente estar ruim ou
fora do ar na hora, rodando testes automáticos na linha, sem precisar passar
por um atendente humano.

## Documentação
- [docs/case.md](docs/case.md) — o case completo
- [docs/modelos.md](docs/modelos.md) — análise e escolha do modelo
- [docs/fontes.md](docs/fontes.md) — fontes consultadas
- [docs/arquitetura.md](docs/arquitetura.md) — arquitetura da Parte 2
- [docs/grafo.md](docs/grafo.md) — nós, arestas, estado, términos
- [docs/rag.md](docs/rag.md) — recuperação e medição
- [docs/memoria.md](docs/memoria.md) — memória semântica, episódica e procedural
- [docs/humano.md](docs/humano.md) — aprovação humana da visita
- [docs/prompts.md](docs/prompts.md) — prompts e versões
- [docs/io.md](docs/io.md) — entradas e saídas reais
- [docs/experimento_frase.md](docs/experimento_frase.md) — experimento de remoção de uma frase do prompt

## Dados simulados

`provedor.db` é gerado por `python -m src.db` (não commitado, está no
`.gitignore`). Os casos nomeados no case (`docs/case.md` §2.8):

- **C001** — simples, resolve com reinício.
- **C002** — divergência: sistema mostra `ONLINE`, cliente diz que caiu.
- **C999** — não existe na base (registro inexistente).
- **C004** — falha física (sinal ≤ −27 dBm), reinício não resolve, precisa agendar.
- **C005** — bairro em manutenção, não deve agendar visita individual.

## Como rodar

Python **3.13** (o 3.14 quebra o `pydantic_core`). Os comandos abaixo são do
PowerShell; no Linux e no macOS, troque a ativação por `source .venv/bin/activate`.

```powershell
git clone <url-do-repo>
cd <pasta-do-repo>
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt --retries 10 --timeout 60
copy .env.example .env
# editem o .env com LLM_BASE_URL, OPENAI_API_KEY e LLM_MODEL (nunca commitem o .env)
python -m src.db          # cria o banco simulado
python -m src.agent C001 "minha internet caiu"
```

## Como rodar os testes

Testes automatizados (grafo com modelo simulado, aprovação humana, RAG,
memória, limites das ferramentas). Não dependem do modelo nem de chave de
API:

```powershell
python -m pytest tests -q
```

## Como usar

**O que a pessoa digita:** o número do contrato (C001, C002, C004, C005, ou
C999 para o caso de erro) e uma frase livre descrevendo o problema, como
argumentos de linha de comando. Opções para scripts: `--decisao
aprovar|rejeitar|editar|expirou`, `--data AAAA-MM-DD` (com `editar`) e
`--rotulo` (nome do log).

**O que o sistema faz:** uma regra em código separa o que vai para um
atendente (fatura, cancelamento, pedido de humano) e o que ainda não descreve
um problema de conexão (pede detalhes, sem chamar o modelo). O restante vai
para o agente, que testa a linha, tenta resolver à distância e, se não
conseguir, propõe uma visita. O modelo não agenda: só o nó de agendamento
agenda, depois da aprovação do cliente.

**O que acontece quando o grafo para.** Ao propor a visita, o grafo pausa no
nó `aprovacao` e o terminal mostra a ação exata e as opções. O estado fica
gravado no checkpoint e a execução só continua com a resposta de quem decide.
Exemplo real (`logs/caso_C004_pausa_edita.json`): o grafo propôs 2026-10-20, a
resposta foi `editar` com 2026-10-22, o código validou a data e agendou nela.
Detalhes, as quatro saídas e o prazo em [docs/humano.md](docs/humano.md).

```
=== APROVAÇÃO NECESSÁRIA ===
Ação: agendar_visita_tecnico  contrato=C004  data=2026-10-20
Consequência: desloca um técnico até a casa do cliente; tem custo e não é desfeito sozinho
Prazo: 900s. Opções: aprovar | rejeitar | editar AAAA-MM-DD
```

**Que saída a pessoa recebe:** no terminal, a resposta ao cliente, as fontes
usadas, o motivo de parada e o caminho do log. Em `logs/caso_<contrato>.json`
(ou no nome dado por `--rotulo`), a trajetória completa (cada ferramenta
chamada, argumentos e resultado), as pausas de aprovação, o commit, os
prompts em uso e a resposta final.

**Exemplo real** (copiado de `logs/caso_C001_feliz.json`, gerado por `python -m scripts.gerar_io`):
<!-- EXEMPLO:INICIO -->
```
$ python -m src.agent C001 "A luz do modem está piscando vermelha e a internet caiu."
Resposta: Pronto, a linha voltou a ficar ONLINE e o sinal está estável (-22 dBm). A luz vermelha deve apagar em alguns minutos.

Se a internet cair de novo, me avise que eu rodo o teste outra vez.
Fontes: [('ferramenta', 'conferir_queda_bairro'), ('ferramenta', 'reiniciar_conexao'), ('ferramenta', 'testar_linha')]  suficiente=True
Parou por: resposta_final   Log: logs/caso_C001_feliz.json
```
Nesta execução o grafo não precisou pausar (nenhuma visita foi proposta).
Commit 8b9fd3d, 2026-10-19T01:38:50.
<!-- EXEMPLO:FIM -->

**O que o sistema não faz:** não responde sobre cobrança, fatura ou
cancelamento (escala para humano); não inventa resposta fora do manual (recusa
e oferece um atendente); não agenda visita sem a aprovação do cliente; não
agenda visita individual se o bairro estiver em manutenção. Se passar de 6
voltas, 8 chamadas de ferramenta, 12000 tokens ou 120 s sem resolver, encerra e
encaminha para um atendente humano.

## Como rodar os casos da Parte 2

Precisam do modelo real (`.env` preenchido). Os rótulos são C001, C002, C999,
C005, FORA, C004, C004B, INC, AMB e ESC (10 casos); sem argumentos rodam todos.

```powershell
python -m scripts.rodar_casos --reset   # 10 casos com o modelo real, logs em logs/
python -m scripts.rodar_casos --reset C004 C004B   # só a prova de aprovação repetida
python -m scripts.gerar_io              # monta docs/io.md e atualiza o exemplo deste README
python -m scripts.experimento_frase 5   # remove uma frase do prompt, 5 execuções por variante
```

Sem modelo:

```powershell
python conferir_grafo.py                # nós e arestas do grafo compilado
python -m scripts.medir_rag --k 1 --k 3 # recuperação do RAG
python -m scripts.demo_reducer          # escrita paralela sem reducer é erro
python -m scripts.demo_idempotencia     # aprovar duas vezes agenda uma vez
python -m scripts.demo_remocao          # grava, varre, remove e varre de novo
```

## Limpeza de logs antigos

Os logs em `logs/` seguem um prazo de retenção de 30 dias (justificativa
em `docs/modelos.md` §5). Para aplicar:

```powershell
python -m scripts.limpar_logs_antigos --simular   # só lista o que seria removido
python -m scripts.limpar_logs_antigos             # remove de fato
```
