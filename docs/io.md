# Entrada e saída do sistema

Exemplos reais, gerados por scripts/gerar_io.py a partir dos logs em logs/.
A entrada é texto livre; o contrato vem da sessão e o thread_id é gerado pelo sistema.
A saída é validada (src/schemas.py): resultado, fontes, suficiente.

## caso_C001_feliz

**O que ler:** Caminho feliz, sem visita. Leia as ferramentas chamadas e as fontes: cada afirmação da resposta aponta para uma ferramenta ou para um trecho do manual (S01) que o sistema confirmou ter sido recuperado.

- data: 2026-10-19T01:38:50, commit: 8b9fd3d, modelo: qwen/qwen3.8-27b, temperature: 0.2
- prompts: {"sistema": {"arquivo": "suporte_v2.md", "sha256": "8ff597289d95"}, "procedural": {"arquivo": "procedural.md", "sha256": "5ecc9d266e5f"}}
- entrada: contrato C001, thread_id C001:c73c6628, mensagem: "A luz do modem está piscando vermelha e a internet caiu."
- ferramentas chamadas: testar_linha, conferir_queda_bairro, reiniciar_conexao, testar_linha
- consultas ao corpus: 0 (sem trecho útil: 0); voltas: 4; tokens: 6005
- pausas de aprovação: nenhuma
- motivo de término: resposta_final
- objeto de saída completo:

```json
{
  "resultado": "Pronto, a linha voltou a ficar ONLINE e o sinal está estável (-22 dBm). A luz vermelha deve apagar em alguns minutos.\n\nSe a internet cair de novo, me avise que eu rodo o teste outra vez.",
  "fontes": [
    {
      "tipo": "ferramenta",
      "id": "conferir_queda_bairro",
      "detalhe": null
    },
    {
      "tipo": "ferramenta",
      "id": "reiniciar_conexao",
      "detalhe": null
    },
    {
      "tipo": "ferramenta",
      "id": "testar_linha",
      "detalhe": null
    }
  ],
  "suficiente": true,
  "motivo_insuficiencia": null,
  "encaminhar_humano": false,
  "motivo_parada": "resposta_final",
  "citacoes_invalidas": []
}
```

## caso_C002_divergencia

**O que ler:** Recusa por regra de código. O bairro está em manutenção; leia pausas de aprovação (nenhuma) e a ausência de visita agendada.

- data: 2026-10-19T01:39:17, commit: 8b9fd3d, modelo: qwen/qwen3.8-27b, temperature: 0.2
- prompts: {"sistema": {"arquivo": "suporte_v2.md", "sha256": "8ff597289d95"}, "procedural": {"arquivo": "procedural.md", "sha256": "5ecc9d266e5f"}}
- entrada: contrato C002, thread_id C002:7c4c69e3, mensagem: "Minha internet caiu, nada navega aqui em casa."
- ferramentas chamadas: testar_linha, conferir_queda_bairro, consultar_base_conhecimento
- consultas ao corpus: 1 (sem trecho útil: 0); voltas: 3; tokens: 4513
- pausas de aprovação: nenhuma
- motivo de término: resposta_final
- objeto de saída completo:

```json
{
  "resultado": "A linha do seu contrato está online e o sinal está bom (-18 dBm). O problema é que o seu bairro, Jardim Ipê, está em manutenção geral de rede — a equipe já está atuando no local.\n\nPor isso não vou agendar visita individual. Enquanto a manutenção não termina, pode ser que a navegação fique instável.\n\nEnquanto isso, teste em outro aparelho e reinicie o roteador. Se o problema persistir mesmo assim, me avise.",
  "fontes": [
    {
      "tipo": "ferramenta",
      "id": "conferir_queda_bairro",
      "detalhe": null
    },
    {
      "tipo": "ferramenta",
      "id": "testar_linha",
      "detalhe": null
    }
  ],
  "suficiente": true,
  "motivo_insuficiencia": null,
  "encaminhar_humano": false,
  "motivo_parada": "resposta_final",
  "citacoes_invalidas": []
}
```

## caso_C004_aprovacao_repetida

**O que ler:** Mesma aprovação repetida. Leia resultado.ja_existia=true: nenhuma segunda visita foi criada.

- data: 2026-10-19T01:42:10, commit: 8b9fd3d, modelo: qwen/qwen3.8-27b, temperature: 0.2
- prompts: {"sistema": {"arquivo": "suporte_v2.md", "sha256": "8ff597289d95"}, "procedural": {"arquivo": "procedural.md", "sha256": "5ecc9d266e5f"}}
- entrada: contrato C004, thread_id C004:23eb916f, mensagem: "Sem internet nenhuma, a luz está vermelha."
- ferramentas chamadas: testar_linha, conferir_queda_bairro, obter_data_atual, propor_visita
- consultas ao corpus: 0 (sem trecho útil: 0); voltas: 4; tokens: 6498
- pausas de aprovação: [('2026-10-20', {'decisao': 'editar', 'data': '2026-10-22'})]
- motivo de término: resposta_final
- objeto de saída completo:

```json
{
  "resultado": "A visita técnica foi agendada para **22/10/2026**. Um técnico irá até o seu endereço para verificar a falha física na linha.",
  "fontes": [
    {
      "tipo": "ferramenta",
      "id": "conferir_queda_bairro",
      "detalhe": null
    },
    {
      "tipo": "ferramenta",
      "id": "obter_data_atual",
      "detalhe": null
    },
    {
      "tipo": "ferramenta",
      "id": "propor_visita",
      "detalhe": null
    },
    {
      "tipo": "ferramenta",
      "id": "testar_linha",
      "detalhe": null
    },
    {
      "tipo": "ferramenta",
      "id": "agendar_visita_tecnico",
      "detalhe": null
    }
  ],
  "suficiente": true,
  "motivo_insuficiencia": null,
  "encaminhar_humano": false,
  "motivo_parada": "resposta_final",
  "citacoes_invalidas": []
}
```

## caso_C004_pausa_edita

**O que ler:** Pausa de aprovação. Leia pausas de aprovação: data proposta, decisão editar e data final já validada pelo código.

- data: 2026-10-19T01:41:16, commit: 8b9fd3d, modelo: qwen/qwen3.8-27b, temperature: 0.2
- prompts: {"sistema": {"arquivo": "suporte_v2.md", "sha256": "8ff597289d95"}, "procedural": {"arquivo": "procedural.md", "sha256": "5ecc9d266e5f"}}
- entrada: contrato C004, thread_id C004:3c17344b, mensagem: "Sem internet nenhuma, a luz está vermelha."
- ferramentas chamadas: testar_linha, obter_data_atual, propor_visita
- consultas ao corpus: 0 (sem trecho útil: 0); voltas: 4; tokens: 5924
- pausas de aprovação: [('2026-10-20', {'decisao': 'editar', 'data': '2026-10-22'})]
- motivo de término: resposta_final
- objeto de saída completo:

```json
{
  "resultado": "A visita técnica foi **agendada para 22/10/2026**. A equipe técnica vai até você para resolver a falha física na linha.\n\nSe o problema voltar antes disso, me avise.",
  "fontes": [
    {
      "tipo": "ferramenta",
      "id": "obter_data_atual",
      "detalhe": null
    },
    {
      "tipo": "ferramenta",
      "id": "propor_visita",
      "detalhe": null
    },
    {
      "tipo": "ferramenta",
      "id": "testar_linha",
      "detalhe": null
    },
    {
      "tipo": "ferramenta",
      "id": "agendar_visita_tecnico",
      "detalhe": null
    }
  ],
  "suficiente": true,
  "motivo_insuficiencia": null,
  "encaminhar_humano": false,
  "motivo_parada": "resposta_final",
  "citacoes_invalidas": []
}
```

## caso_C004_terminal

**O que ler:** Mesma pausa de aprovação, mas decidida pelo terminal (decisor interativo). Leia a data final escolhida e o resultado do agendamento.

- data: 2026-10-18T12:17:18, commit: sem-git, modelo: qwen/qwen3.8-27b, temperature: 0.2
- prompts: "não registrado"
- entrada: contrato C004, thread_id C004:9a2bbe3e, mensagem: "Sem internet nenhuma, a luz está vermelha."
- ferramentas chamadas: testar_linha, conferir_queda_bairro, obter_data_atual, propor_visita
- consultas ao corpus: 0 (sem trecho útil: 0); voltas: 4; tokens: 6472
- pausas de aprovação: [('2026-10-19', {'decisao': 'editar', 'data': '2026-10-22'})]
- motivo de término: resposta_final
- objeto de saída completo:

```json
{
  "resultado": "A visita técnica foi **agendada para 22/10/2026**. Um técnico irá até você para resolver a falha física na linha.\n\nEnquanto isso, não há nada que você possa fazer por sua conta — a luz vermelha e o sinal de -30 dBm indicam um problema no cabo ou no equipamento que só a visita resolve.\n\nPosso ajudar em mais alguma coisa?",
  "fontes": [
    {
      "tipo": "ferramenta",
      "id": "conferir_queda_bairro",
      "detalhe": null
    },
    {
      "tipo": "ferramenta",
      "id": "obter_data_atual",
      "detalhe": null
    },
    {
      "tipo": "ferramenta",
      "id": "propor_visita",
      "detalhe": null
    },
    {
      "tipo": "ferramenta",
      "id": "testar_linha",
      "detalhe": null
    },
    {
      "tipo": "ferramenta",
      "id": "agendar_visita_tecnico",
      "detalhe": null
    }
  ],
  "suficiente": true,
  "motivo_insuficiencia": null,
  "encaminhar_humano": false,
  "motivo_parada": "resposta_final",
  "citacoes_invalidas": []
}
```

## caso_C005_nao_agenda

**O que ler:** O cliente pediu técnico, mas o bairro está em manutenção. Leia que propor_visita foi recusada e nada foi agendado.

- data: 2026-10-19T01:40:02, commit: 8b9fd3d, modelo: qwen/qwen3.8-27b, temperature: 0.2
- prompts: {"sistema": {"arquivo": "suporte_v2.md", "sha256": "8ff597289d95"}, "procedural": {"arquivo": "procedural.md", "sha256": "5ecc9d266e5f"}}
- entrada: contrato C005, thread_id C005:2d48a346, mensagem: "Estou sem internet, quero que mandem um técnico hoje."
- ferramentas chamadas: testar_linha, conferir_queda_bairro
- consultas ao corpus: 0 (sem trecho útil: 0); voltas: 2; tokens: 2850
- pausas de aprovação: nenhuma
- motivo de término: resposta_final
- objeto de saída completo:

```json
{
  "resultado": "Sua linha está offline, mas o sinal está bom (-19 dBm), então não é falha física. O problema é que o seu bairro, Jardim Ipê, está em manutenção geral de rede.\n\nComo a equipe de rede já está atuando na região, não consigo agendar uma visita técnica individual. A manutenção deve resolver a queda para todos os clientes do bairro.\n\nPosso ajudar com mais alguma coisa?",
  "fontes": [
    {
      "tipo": "ferramenta",
      "id": "conferir_queda_bairro",
      "detalhe": null
    },
    {
      "tipo": "ferramenta",
      "id": "testar_linha",
      "detalhe": null
    }
  ],
  "suficiente": true,
  "motivo_insuficiencia": null,
  "encaminhar_humano": false,
  "motivo_parada": "resposta_final",
  "citacoes_invalidas": []
}
```

## caso_C999_inexistente

**O que ler:** Entrada incompleta pelo lado do cadastro: o contrato não existe. Leia suficiente=false e o encaminhamento humano.

- data: 2026-10-19T01:39:39, commit: 8b9fd3d, modelo: qwen/qwen3.8-27b, temperature: 0.2
- prompts: {"sistema": {"arquivo": "suporte_v2.md", "sha256": "8ff597289d95"}, "procedural": {"arquivo": "procedural.md", "sha256": "5ecc9d266e5f"}}
- entrada: contrato C999, thread_id C999:61c1f55c, mensagem: "Minha internet caiu."
- ferramentas chamadas: testar_linha, conferir_queda_bairro
- consultas ao corpus: 0 (sem trecho útil: 0); voltas: 2; tokens: 2781
- pausas de aprovação: nenhuma
- motivo de término: resposta_final
- objeto de saída completo:

```json
{
  "resultado": "O sistema não localizou o contrato C999, então não consegui testar a linha nem o bairro.\n\nPosso tentar de novo, ou prefere que eu encaminhe para um atendente humano?",
  "fontes": [],
  "suficiente": false,
  "motivo_insuficiencia": "sem_fonte",
  "encaminhar_humano": false,
  "motivo_parada": "resposta_final",
  "citacoes_invalidas": []
}
```

## caso_entrada_ambigua

**O que ler:** Entrada ambígua. Leia a frase em que o modelo declara qual leitura escolheu antes de seguir.

- data: 2026-10-19T01:42:36, commit: 8b9fd3d, modelo: qwen/qwen3.8-27b, temperature: 0.2
- prompts: {"sistema": {"arquivo": "suporte_v2.md", "sha256": "8ff597289d95"}, "procedural": {"arquivo": "procedural.md", "sha256": "5ecc9d266e5f"}}
- entrada: contrato C001, thread_id C001:0051a4dd, mensagem: "A internet está ruim hoje, não sei se é o wifi ou a internet mesmo."
- ferramentas chamadas: testar_linha
- consultas ao corpus: 0 (sem trecho útil: 0); voltas: 2; tokens: 3183
- pausas de aprovação: nenhuma
- motivo de término: resposta_final
- objeto de saída completo:

```json
{
  "resultado": "A linha está online e o sinal está bom (-22 dBm). Então o problema provavelmente é no wifi, não na internet.\n\nPra confirmar, me ajuda com um teste:\n- Conecta um aparelho direto no roteador por cabo de rede (ethernet) e tenta navegar.\n\nSe funcionar pelo cabo, o problema é no wifi. Se não funcionar nem pelo cabo, me avisa que eu confiro se há queda no bairro.\n\nTambém vale tentar reiniciar o roteador (desligar por 10 segundos e ligar de novo).\n\nQuer que eu já reinicie a conexão à distância?",
  "fontes": [
    {
      "tipo": "ferramenta",
      "id": "testar_linha",
      "detalhe": null
    }
  ],
  "suficiente": true,
  "motivo_insuficiencia": null,
  "encaminhar_humano": false,
  "motivo_parada": "resposta_final",
  "citacoes_invalidas": []
}
```

## caso_entrada_incompleta

**O que ler:** Entrada incompleta. Leia que nenhuma ferramenta foi chamada e que a resposta pergunta o que falta.

- data: 2026-10-19T01:42:10, commit: 8b9fd3d, modelo: qwen/qwen3.8-27b, temperature: 0.2
- prompts: {"sistema": {"arquivo": "suporte_v2.md", "sha256": "8ff597289d95"}, "procedural": {"arquivo": "procedural.md", "sha256": "5ecc9d266e5f"}}
- entrada: contrato C001, thread_id C001:f8c14d80, mensagem: "não funciona"
- ferramentas chamadas: nenhuma
- consultas ao corpus: 0 (sem trecho útil: 0); voltas: 0; tokens: 0
- pausas de aprovação: nenhuma
- motivo de término: entrada_incompleta
- objeto de saída completo:

```json
{
  "resultado": "Não consegui entender qual é o problema. Para eu poder ajudar, me conte: o que a luz do modem mostra (verde, vermelha, piscando ou apagada) e se a falha acontece em todos os aparelhos ou só em um.",
  "fontes": [],
  "suficiente": false,
  "motivo_insuficiencia": "entrada_incompleta",
  "encaminhar_humano": false,
  "motivo_parada": "entrada_incompleta",
  "citacoes_invalidas": []
}
```

## caso_fora_do_corpus

**O que ler:** Pergunta técnica fora do corpus. Leia que o portão do RAG barrou a resposta e o texto fixo de recusa, com suficiente=false.

- data: 2026-10-19T01:40:27, commit: 8b9fd3d, modelo: qwen/qwen3.8-27b, temperature: 0.2
- prompts: {"sistema": {"arquivo": "suporte_v2.md", "sha256": "8ff597289d95"}, "procedural": {"arquivo": "procedural.md", "sha256": "5ecc9d266e5f"}}
- entrada: contrato C001, thread_id C001:003c0fce, mensagem: "Como faço para abrir portas no roteador para jogar online?"
- ferramentas chamadas: consultar_base_conhecimento
- consultas ao corpus: 1 (sem trecho útil: 1); voltas: 2; tokens: 3010
- pausas de aprovação: nenhuma
- motivo de término: resposta_final
- objeto de saída completo:

```json
{
  "resultado": "Não encontrei essa informação nos manuais do suporte técnico. Posso encaminhar você para um atendente humano.",
  "fontes": [],
  "suficiente": false,
  "motivo_insuficiencia": "fora_do_corpus",
  "encaminhar_humano": true,
  "motivo_parada": "resposta_final",
  "citacoes_invalidas": []
}
```

## caso_fora_do_escopo

**O que ler:** Fora do escopo (cancelamento e desconto). Leia a triagem por código: o modelo nem foi chamado e o texto diz o que o sistema faz.

- data: 2026-10-19T01:42:36, commit: 8b9fd3d, modelo: qwen/qwen3.8-27b, temperature: 0.2
- prompts: {"sistema": {"arquivo": "suporte_v2.md", "sha256": "8ff597289d95"}, "procedural": {"arquivo": "procedural.md", "sha256": "5ecc9d266e5f"}}
- entrada: contrato C001, thread_id C001:fc6b9c98, mensagem: "Quero cancelar meu plano e pedir um desconto."
- ferramentas chamadas: nenhuma
- consultas ao corpus: 0 (sem trecho útil: 0); voltas: 0; tokens: 0
- pausas de aprovação: nenhuma
- motivo de término: encaminhado_humano
- objeto de saída completo:

```json
{
  "resultado": "Esse assunto (cobrança, fatura, cancelamento ou pedido de atendente) não é do suporte técnico. Aqui eu testo a linha, confiro queda no bairro, reinicio a conexão e proponho visita técnica. Vou encaminhar você para um atendente humano.",
  "fontes": [],
  "suficiente": false,
  "motivo_insuficiencia": "encaminhado_humano",
  "encaminhar_humano": true,
  "motivo_parada": "encaminhado_humano",
  "citacoes_invalidas": []
}
```

## Prova de aprovação repetida

- primeira execução (C004:3c17344b): {"contrato": "C004", "data": "2026-10-22", "status": "AGENDADA", "ja_existia": false}
- segunda execução, mesma aprovação (C004:23eb916f): {"contrato": "C004", "data": "2026-10-22", "status": "AGENDADA", "ja_existia": true}
- ja_existia=true na segunda indica que o código reconheceu a visita pela chave (contrato, data) e não criou outra.
