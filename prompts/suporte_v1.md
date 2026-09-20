# Prompt: agente de suporte técnico doméstico — v1

**Modelo testado:** qwen/qwen3.8-27b (via Groq), temperature=0.2
**Técnica:** zero-shot com contrato de saída explícito.
**Por que zero-shot:** a tarefa é curta (triagem + no máximo 2 ferramentas
de leitura antes de agir) e as regras que importam são restrições de
segurança, não exemplos de estilo — few-shot aumentaria o prompt sem reduzir
erro nesta versão.

## Contrato de saída
- Nunca responde sobre cobrança, fatura ou desconto — encaminha para humano.
- Nunca chama `agendar_visita_tecnico` com `confirmado_pelo_cliente=true`
  sem o cliente ter dito "sim" explicitamente na conversa.
- Nunca diz "resolvido" sem rodar `testar_linha` de novo depois de
  `reiniciar_conexao`.
- Nunca pergunta ao cliente qual data ele prefere para a visita técnica —
  chama `obter_data_atual` e propõe o dia seguinte ao de hoje (regra do
  domínio, case §2.1); só pede a confirmação.

## O que cada regra impede
- A regra de cobrança impede o agente de prometer descontos ou alterar
  contrato — fora do que ele tem permissão de fazer (case §2.1).
- A regra de confirmação impede agendar visita (custo real de deslocamento)
  sem autorização do cliente.
- A regra de checagem dupla impede fechar o atendimento com a internet
  ainda fora do ar (o caso "vai e volta" do case §2.11).
- A regra da data impede empurrar para o cliente uma decisão que é do
  sistema (o próprio agente sabe qual é o prazo, não precisa perguntar) —
  sem isso, o modelo tende a perguntar "qual data você prefere?" em vez de
  seguir a regra de "no máximo o dia seguinte". A primeira versão tentava
  resolver isso injetando a data no texto do prompt; preferimos dar isso
  como ferramenta (`obter_data_atual`) porque é mais fácil de testar
  isoladamente e porque, se um dia o agente precisar de mais do que a data
  (hora, fuso do cliente), já existe um lugar natural para isso crescer.

## Texto do prompt
Ver `SYSTEM_PROMPT` em `src/agent.py` — mantido em um único lugar para não
haver duas versões divergentes. Ao mudar o prompt, copiem a versão anterior
para `prompts/suporte_v0.md` antes de editar `agent.py`, para manter o
histórico de versões pedido no enunciado.