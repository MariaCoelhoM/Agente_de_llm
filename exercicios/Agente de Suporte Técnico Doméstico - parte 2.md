<!-- Transcrição fiel do PDF "Agente de Suporte Técnico Doméstico - parte 2.pdf" (material do grupo, Parte 1). O PDF foi removido do repositório; o conteúdo está aqui. -->

# Como Funciona o Robô de Suporte Técnico

## 1. O que Entra

- **De onde vem as mensagens:**
  - A maioria vem do WhatsApp do próprio cliente reclamando de um problema.
  - Uma pequena parte vem de um aviso automático do sistema quando ele percebe sozinho que a internet caiu em um bairro inteiro.
- **O que as pessoas costumam pedir:**
  - 70% Problemas simples de internet ("caiu", "está lenta", "luz vermelha no aparelho").
  - 15% Pedidos de ajuda para configurar algo (ex.: trocar a senha do Wi-Fi).
  - 10% Assuntos que não são do suporte técnico (cobrança, cancelamento, pedir desconto).
  - 5% Avisos automáticos de queda geral no bairro.

Como chegam coisas muito diferentes, o robô precisa separar as mensagens no início para não tentar resolver um problema de cobrança usando um teste de internet.

## 2. As Regras do Robô

**O Papel do Robô (em uma frase):** "Você é um assistente que testa a internet do cliente e resolve coisas simples à distância (reiniciar a conexão, trocar a senha do Wi-Fi). Se o problema for físico no cabo ou na rede, você explica o que houve e ajuda a agendar um técnico. Você nunca resolve dúvidas sobre dinheiro/faturas e não cobra nada do cliente sem a aprovação dele."

**As Ferramentas do Robô:**

- **Testar a linha:** Não altera nada, só lê a situação atual da internet.
- **Conferir queda no bairro:** Checa se mais pessoas perto estão sem internet.
- **Reiniciar a conexão:** Tenta arrumar a internet à distância (pode ser feito quantas vezes precisar).
- **Mudar a senha do Wi-Fi:** Altera o Wi-Fi do cliente.
- **Agendar visita do técnico:** Só faz se o cliente confirmar, pois gera custo de deslocamento.
- **Abrir pedido de desconto:** O robô não dá o desconto; ele só cria um pedido para um funcionário humano analisar.

**A Memória do Robô (o que ele precisa guardar durante a conversa):**

- O número do contrato do cliente.
- O resultado dos últimos testes.
- Se já tentou reiniciar a internet.
- Se o bairro todo está sem sinal.
- Se está esperando a resposta do cliente para agendar a visita.

**Limites de Segurança:**

- No máximo 3 testes de linha por atendimento (para não entrar em loop infinito).
- No máximo 6 mensagens trocadas. Se não resolver até aí, passa para um atendente humano.
- No máximo 5 minutos de tempo total de atendimento.

## 3. O Passo a Passo da Solução

```
1. MENSAGEM DO CLIENTE ➔ O cliente escreve no WhatsApp ou o sistema avisa de uma queda.
   ↓
2. SEPARAÇÃO ─────────── ➔ O robô lê e decide o caminho:
                            • Técnico? Vai para o passo 3.
                            • Configuração simples? Troca a senha direto.
                            • Cobrança/Outros? Manda para um atendente humano.
                            • Queda no bairro? Avisa direto no passo 6 sem testar um por um.
   ↓
3. TESTE E DIAGNÓSTICO ➔ Faz testes na linha e descobre o problema (máximo 3 testes).
   ↓
4. AÇÃO À DISTÂNCIA ─── ➔ Tenta resolver sozinho (ex.: reinicia o sinal).
   ↓
5. VERIFICAÇÃO ──────── ➔ Checa se a internet voltou:
                            • Voltou? Vai para o encerramento (passo 7/8).
                            • Não voltou? Decide se precisa de técnico ou de atendente.
   ↓
6. AGENDAMENTO ──────── ➔ Se a internet não voltou, sugere datas e horários para o
                          técnico ir até a casa (só com o "SIM" do cliente).
   ↓
7. REGISTRO ─────────── ➔ Salva tudo o que aconteceu no sistema.
   ↓
8. RESPOSTA FINAL ────── ➔ Responde ao cliente no WhatsApp de forma simples.
```

**Exemplo de Conversa (O que o cliente vê no final):**

> "Pronto! O sinal voltou ao normal e seu aparelho já conectou. Pode tentar usar a internet agora?"

**Por que o sistema foi feito desse jeito?**

1. **Separação no início:** As pessoas escrevem de jeitos muito diferentes. Um filtro inteligente entende a intenção do cliente em vez de só procurar palavras soltas.
2. **Testes inteligentes:** O robô decide qual teste fazer com base no resultado do teste anterior (se a luz está apagada, não adianta tentar mudar a senha do Wi-Fi).
3. **Checagem dupla:** Depois de reiniciar o aparelho, o robô confere se a internet realmente voltou antes de dizer ao cliente que está tudo resolvido.
4. **Proteção contra custos:** Agendar técnico e pedir desconto custam dinheiro para a empresa. Por isso, o robô nunca faz isso sozinho sem a autorização do cliente ou sem passar para um humano.

---

# Arquitetura — Agente de Apoio ao Técnico de Campo

## 1. Entrada

- **Quem dispara:** O técnico de rua (via WhatsApp/Telegram do trabalho ou app interno) ao chegar no endereço do cliente ou durante o atendimento.
- **O que envia:**
  - Áudios e textos rápidos ("Cheguei na casa do cliente", "A luz PON da ONT tá piscando rápido")
  - Fotos e imagens (foto do conector óptico, foto dos LEDs do modem, foto do medidor de sinal/Power Meter)
  - Comandos curtos ("muda a Vlan", "provisiona a ONT nova")

## 2. System Prompt & Ferramentas

**Papel do Agente (em uma frase):** "Você é o assistente técnico de campo: apoia o técnico na rua rodando testes avançados de fibra/sinal, executando provisionamento de equipamentos e validando o serviço antes do encerramento da visita."

**Ferramentas do Agente do Técnico:**

- `consultar_historico_atendimento(id_chamado)`: Lê o que o robô do cliente testou antes da visita.
- `medir_sinal_optico_porta(id_caixa)`: Checa se a caixa da rua (CTO) tem perda de sinal antes de mexer na casa do cliente.
- `provisionar_novo_modem(mac_antigo, mac_novo)`: Troca o equipamento no sistema sem o técnico precisar ligar para a central/NOC.
- `validar_qualidade_pos_instalacao()`: Roda uma bateria de testes rigorosos de sinal e velocidade para garantir que o conserto funcionou.
- `fechar_chamado_tecnico(id_chamado, relatorio_foto)`: Encerra a visita no sistema.

## 3. O Passo a Passo no Campo

```
1. CHEGADA ──────────── ➔ Técnico avisa que chegou. O robô resume o histórico:
                          "Cliente reclamou de sinal fraco. Teste remoto indicou perda na fibra."
2. DIAGNÓSTICO LOCAL ── ➔ Técnico manda foto da medição de sinal ou foto do cabo dobrado.
                          O robô identifica a falha visual/técnica e sugere o reparo.
3. TROCA / CONFIG ───── ➔ Técnico troca o modem e envia a foto da etiqueta com o código MAC.
                          O robô cadastra o equipamento novo no sistema automaticamente.
4. VALIDAÇÃO DE SAÍDA ─ ➔ O robô roda o teste final de sinal na linha.
                          Se der tudo ok (ex.: "Status: ONLINE, Sinal: -19dBm"), autoriza o fecho.
5. BAIRXA E FECHAMENTO ─ ➔ O robô grava a foto da instalação concluída e encerra a visita.
```

## 4. Por que essa dupla (Agente Cliente + Agente Técnico) funciona tão bem?

- **Elimina o "Atendimento da Central" (NOC):** O técnico na rua não perde 15 a 20 minutos no telefone esperando a central liberar ou cadastrar um modem novo. Ele faz tudo conversando direto com o robô em segundos.
- **Validação de Qualidade com Visão Computacional:** O técnico envia a foto da fusão de fibra ou do conector, e o robô valida se a instalação segue o padrão de qualidade da empresa antes de fechar o chamado.
- **Garante o Fechamento do Ciclo:** O robô do cliente detectou a falha ➔ Agendou a visita ➔ O robô do técnico ajudou a consertar e testou ➔ O robô do cliente envia uma mensagem final para o cliente: "Seu técnico finalizou o conserto! A internet já está operando 100%."
