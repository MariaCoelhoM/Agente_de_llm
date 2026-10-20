# RAG: recuperação de conhecimento

## 1. As formas usadas

| Forma usada | Com o quê | O que responde no case |
|---|---|---|
| consulta estruturada | `testar_linha` e `conferir_queda_bairro`, sobre o SQLite `provedor.db` | as duas perguntas de registro (Q11, Q12): o estado da linha e do bairro agora |
| busca textual | BM25 implementado no projeto (`src/rag.py`), sem embeddings | as dez perguntas de termo e assunto (Q01 a Q10) |

Busca vetorial não é usada. A pergunta "o RAG é vetorial ou é banco de dados?" tem resposta: **os dois no sentido do enunciado, sem o vetorial**: banco de dados para o estado atual e busca textual para o conhecimento dos manuais.

A decisão revisa a `base-de-conhecimento-v1`, que previa embeddings com numpy. Os motivos: o corpus tem 27 trechos; as perguntas usam o vocabulário do domínio (dBm, luz vermelha, bairro em manutenção); e não há API de embedding gratuita e estável, o que a restrição do grupo (nada pago nem gratuito por tempo limitado) exclui. O custo está na §5: busca lexical não acha paráfrase sem palavra em comum, e o stemmer é só remoção de plural.

## 2. As perguntas e a classificação

As 12 perguntas estão em `dados/perguntas_rag.json`, cada uma com o trecho que a responde. O resultado vem de `python -m scripts.medir_rag --k 1 --k 3`.

| Id | Pergunta | Forma | Exceção | Quem responde | Trecho esperado | Resultado |
|---|---|---|---|---|---|---|
| Q01 | o que significa a luz vermelha piscando no meu modem | assunto | não | busca textual | S01 | S01 em 1º |
| Q02 | a partir de quantos dBm o sinal é falha física | termo | não | busca textual | S07, E03, E02 | E02 em 1º; S07 e E03 também no top 3 |
| Q03 | meu bairro está em manutenção, posso agendar visita só para a minha casa | assunto | sim | busca textual | P04, S09 | P04 em 1º, S09 em 2º |
| Q04 | quantos testes de linha o agente pode fazer em um atendimento | termo | não | busca textual | P03 | P03 em 1º |
| Q05 | minha internet cai e volta sozinha, o que devo fazer | assunto | não | busca textual | S06 | S06 em 1º |
| Q06 | o cliente pediu desconto na fatura, o agente pode dar | assunto | sim | busca textual | P02 | P02 em 1º |
| Q07 | qual o prazo máximo para agendar a visita técnica | termo | não | busca textual | P04 | P04 em 1º |
| Q08 | não aparece a rede sem fio nos aparelhos, mas a luz da fibra está boa | assunto | não | busca textual | S04 | S04 em 1º |
| Q09 | o agente consegue trocar a senha do wi-fi do cliente | assunto | sim | busca textual | S14 | S14 em 1º |
| Q10 | quanto custa o plano de 500 mega | assunto | não | nenhuma: não está no corpus | nenhum | barrada pelo portão (cobertura 0,25) |
| Q11 | o meu bairro está em manutenção agora | registro | não | consulta estruturada | nenhum | passa no portão (cobertura 0,67): limitação |
| Q12 | qual é o sinal da minha linha neste momento | registro | não | consulta estruturada | nenhum | passa no portão (cobertura 0,75): limitação |

Composição: três perguntas dependem de uma exceção (Q03, Q06, Q09) e uma não tem resposta no corpus (Q10), que exercita a recusa do contrato de saída.

As perguntas foram escritas pelo grupo junto com o corpus, e os dois são simulados. O vocabulário é compartilhado, então o 9 de 9 é otimista: um cliente real usaria outras palavras.

## 3. O corpus

| Documento | Origem | Mantido por | Trechos | Vigente |
|---|---|---|---|---|
| `01_manual_sintomas` | escrito pelo grupo a partir do domínio do case (simulado) | Equipe de Suporte Técnico Avançado | 14 | sim |
| `02_politicas_atendimento` | idem | Gerência da Operação | 7 | sim |
| `03_equipamentos_limiares` | idem | Equipe de Engenharia de Rede | 6 | sim |
| `04_manual_sintomas_v0` | idem, versão antiga mantida de propósito | Equipe de Suporte Técnico Avançado | 3 | **não**, revogado em 2026-06-01, substituído por `01` |

**Com que frequência mudam.** Não foi medida, porque o corpus é simulado. O que o desenho assume: os limiares mudam quando a rede muda (o próprio E03 fala em "rede atual") e as políticas mudam quando a gerência decide, o que são eventos raros. Por isso o índice é construído uma vez por processo (`obter_indice`) a partir dos arquivos, sem atualização incremental: com 27 trechos reconstruir custa milissegundos, e mudar um documento significa reiniciar o processo.

Cada documento declara no cabeçalho `agente_aplicavel`, `vigente`, `tipo` e `mantido_por`. O filtro de vigência e de agente é aplicado em código, em `construir_indice`, e não é pedido ao modelo.

## 4. Corte, k e portão

Mesmo sem busca vetorial, o documento precisa virar trechos para ser ranqueado.

**Corte.** Por estrutura do documento: cada item `## ID — Título` vira um trecho. O corpus tem itens curtos e numerados (S01, P04, E03), e um item é a unidade que responde uma pergunta. O trecho herda o título do documento no início do texto, porque "no máximo 3 vezes" não faz sentido sozinho.

**k = 3** (`RAG_K`). Com k=1 o acerto@1 já é 9 de 9, então o 3 não vem de ganho de acerto: vem de entregar a exceção junto da regra (Q03 precisa de P04 e S09; Q02 tem três trechos esperados). O custo é pequeno, no máximo 3 trechos curtos.

**Portão de suficiência.** O melhor trecho precisa cobrir ao menos 50% dos termos da pergunta (`RAG_COBERTURA_MINIMA`). Abaixo disso o modelo recebe `suficiente=false` e nenhum trecho para citar. O limiar saiu da medição: Q10 tem cobertura 0,25 e as perguntas com resposta no corpus ficam entre 0,50 e 1,00. Q06 tem 0,50, exatamente no limiar, o que torna o valor frágil: uma palavra a mais na pergunta a faria cair para fora.

## 5. Medição

| Medida | Corpus vigente | Com o documento revogado |
|---|---|---|
| acerto@1 (9 perguntas com resposta no corpus) | 9/9 | 8/9 |
| acerto@3 | 9/9 | 9/9 |
| portão correto (corpus ou nenhuma) | 10/10 | 10/10 |

Limite conhecido: as perguntas de registro (Q11, Q12) passam no portão porque compartilham palavras com o corpus. Quem as desvia para as ferramentas de estado é a descrição da ferramenta (que diz que ela não responde sobre o estado atual da linha ou do bairro), não o portão.

## 6. O documento revogado

`04_manual_sintomas_v0` foi revogado em 2026-06-01 e contradiz o corpus atual em três números: limiar de falha física de -25 dBm (V01, contra -27), 5 reinícios antes da visita (V02) e visita em 3 dias úteis (V03, contra o dia seguinte).

Com ele no índice (`python -m scripts.medir_rag --revogados`):
- Q07 (prazo máximo de visita) passa a trazer V02 e V03 antes de P04: o primeiro trecho é a regra antiga;
- Q02 (limiar de dBm) traz V01 em segundo, entre E02 e E03;
- Q03 traz V02 em terceiro;
- o acerto@1 cai de 9 para 8.

O sistema não descobre sozinho que um documento envelheceu: nada no texto de V01 a V03 os marca como antigos para o ranking. A correção é curadoria, não técnica de recuperação: `vigente: false` no cabeçalho, aplicado em código. `tests/test_rag.py` reproduz o experimento.

## 7. Onde a recuperação entra no laço

**Forma escolhida: ferramenta do agente.** O modelo decide quando consultar (`consultar_base_conhecimento`), como decide chamar qualquer outra ferramenta. A alternativa, uma etapa fixa antes de toda resposta, faria uma busca em toda execução.

**Chamadas de recuperação por execução**, lidas dos 11 logs de 19/10/2026 em `docs/io.md`:

| Caso | Consultas ao corpus | Sem trecho útil |
|---|---|---|
| `caso_C002_divergencia` | 1 | 0 |
| `caso_fora_do_corpus` | 1 | 1 |
| os outros 9 casos | 0 | 0 |
| **total em 11 execuções** | **2 (média de 0,18 por execução)** | **1** |

Com uma etapa fixa seriam 11 buscas em 11 execuções, das quais 9 em atendimentos que não precisaram do manual. A ferramenta economizou essas 9 buscas, ao custo de uma volta a mais nas vezes em que o modelo consultou. O número varia entre execuções do mesmo caso: numa rodada anterior, `caso_C001_feliz` também consultou o manual (S01) e nesta não.

A ferramenta devolve no máximo 3 trechos com id, e a saída final só aceita citações de ids que ela devolveu naquela execução (`docs/arquitetura.md` §9). Uma consulta com `suficiente=false` é registrada na trajetória e conta como consulta sem trecho útil.
