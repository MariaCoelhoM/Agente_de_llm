# Agente de Suporte Técnico Doméstico

## O problema em uma frase
Descobrir e resolver o motivo de a internet da casa do cliente estar ruim ou
fora do ar na hora, rodando testes automáticos na linha, sem precisar passar
por um atendente humano.

## Documentação
- [docs/case.md](docs/case.md) — o case completo
- [docs/modelos.md](docs/modelos.md) — análise e escolha do modelo
- [docs/fontes.md](docs/fontes.md) — fontes consultadas


# Dados simulados

`provedor.db` é gerado por `python3 -m src.db` (não commitado — está no
`.gitignore`). Os casos nomeados no case (`docs/case.md` §2.8):

- **C001** — simples, resolve com reinício.
- **C002** — divergência: sistema mostra `ONLINE`, cliente diz que caiu.
- **C999** — não existe na base (registro inexistente).
- **C004** — falha física (sinal ≤ −27dBm), reinício não resolve, precisa agendar.
- **C005** — bairro em manutenção, não deve agendar visita individual.

## Como rodar

\`\`\`bash
git clone <url-do-repo>
cd <pasta-do-repo>
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# editem o .env com LLM_BASE_URL, OPENAI_API_KEY e LLM_MODEL
python3 -m src.db          # cria o banco simulado
python3 -m src.agent C001 "minha internet caiu"
\`\`\`

## Como usar

**O que a pessoa digita:** o número do contrato (um dos simulados: C001,
C002, C004, C005, ou C999 para testar o caso de erro) e uma frase livre
descrevendo o problema, como argumentos de linha de comando.

**O que o sistema faz:** classifica o pedido, testa a linha do cliente,
tenta resolver à distância e, se não conseguir, propõe agendar uma visita —
só com confirmação explícita do cliente na própria conversa.

**Que saída a pessoa recebe:** no terminal, o motivo de parada do
atendimento e o caminho do log. No arquivo `logs/caso_<contrato>.json`, a
trajetória completa (cada ferramenta chamada, argumentos e resultado) e a
resposta final dada ao cliente.

**Exemplo real** (copiado de `logs/caso_C001.json` depois de rodar):
\`\`\`
$ python3 -m src.agent C001 "Boa noite, minha internet caiu e a luz do aparelho ficou vermelha."
Parou por: resposta_final_do_modelo
Log salvo em: logs/caso_C001.json
\`\`\`
<!-- colem aqui o trecho real de "resposta_final" do log, depois de rodar -->

**O que o sistema não faz:** não responde sobre cobrança, fatura ou
cancelamento (escala para humano); não agenda visita sem "sim" explícito do
cliente; não agenda visita individual se o bairro estiver em manutenção. Se
passar de 6 mensagens sem resolver, encerra e indica transbordo para
atendente humano.