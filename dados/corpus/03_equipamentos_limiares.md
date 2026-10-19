---
doc: 03_equipamentos_limiares
titulo: Equipamentos e limiares técnicos
tipo: equipamento
agente_aplicavel: cliente
vigente: true
mantido_por: Equipe de Engenharia de Rede
---

Documento simulado, escrito pelo grupo a partir do domínio do case. Os valores são do projeto, não de um fabricante real.

## E01 — Significado das luzes do modem
Modelo ONT-X200. Luz de energia verde: equipamento ligado. Luz de sinal óptico verde: fibra conectada. Luz de sinal óptico vermelha piscando: sinal óptico perdido. Luz de sinal óptico vermelha fixa: falha interna do equipamento. Luz de Wi-Fi apagada: rede sem fio desligada.

## E02 — Faixas de sinal óptico
Sinal melhor que -25 dBm: normal. Sinal entre -25 e -27 dBm: zona cinzenta, funciona mas é instável. Sinal igual ou pior que -27 dBm: falha física provável.

## E03 — Limite de falha física
O limiar de falha física da rede atual é -27 dBm. Sinal igual ou abaixo desse valor indica cabo, conector ou fibra com problema, e o reinício remoto não resolve.

## E04 — Reinício remoto
O reinício remoto só é indicado quando não há falha física. Cada reinício conta no contador diário do modem. Não reinicie mais de uma vez no mesmo atendimento sem um novo teste que justifique.

## E05 — Teste de linha
O teste de linha retorna o status (ONLINE ou OFFLINE) e o sinal óptico em dBm. Um status ONLINE com sinal normal indica que a fibra está boa, e o problema está dentro da casa do cliente.

## E06 — Roteador do cliente
O roteador Wi-Fi do cliente é separado do modem óptico. Reiniciar o roteador não altera o sinal óptico. Problemas só de Wi-Fi não aparecem no teste de linha.
