---
doc: 01_manual_sintomas
titulo: Manual de sintomas e diagnóstico
tipo: sintomas
agente_aplicavel: cliente
vigente: true
mantido_por: Equipe de Suporte Técnico Avançado
---

Documento simulado, escrito pelo grupo a partir do domínio do case. Não é um manual real de operadora.

## S01 — Luz vermelha piscando no modem
Categoria: sinal fraco.
Luz vermelha piscando indica queda do sinal óptico que chega na casa. Peça ao cliente para conferir se o cabo de fibra (o cabinho amarelo atrás do modem) está bem encaixado e sem dobra. Depois rode o teste de linha. Se o sinal estiver abaixo de -27 dBm, é falha física e o caso segue para visita técnica.

## S02 — Luz vermelha fixa no modem
Categoria: energia.
Luz vermelha fixa indica falha de energia ou falha interna do equipamento, não problema de sinal. Peça ao cliente para conferir a tomada e a fonte. Se a luz continuar vermelha fixa depois de religar na tomada, encaminhe para visita técnica com troca de equipamento.

## S03 — Modem sem nenhuma luz acesa
Categoria: energia.
Sem luz alguma, o equipamento não está recebendo energia. Peça para conferir a tomada, o filtro de linha e se a fonte está bem encaixada no modem. O agente não consegue testar a linha de um modem desligado.

## S04 — Wi-Fi sumiu, mas as luzes estão verdes
Categoria: wi-fi.
Se a luz da conexão está verde e o Wi-Fi não aparece nos aparelhos, o problema está na rede sem fio do roteador e não na fibra. Oriente o cliente a desligar o roteador por trinta segundos e ligar de novo. O teste de linha deve retornar ONLINE nesse caso.

## S05 — Internet lenta
Categoria: desempenho.
Lentidão com a linha ONLINE costuma vir de muitos aparelhos conectados, distância do roteador ou horário de pico. Peça ao cliente para testar perto do roteador e, se possível, por cabo de rede. Só abra visita técnica se o sinal estiver fora do normal.

## S06 — A internet cai e volta sozinha
Categoria: instabilidade.
Quedas curtas que se resolvem sozinhas são o caso mais difícil: um teste pontual pode pegar a linha num momento normal. Rode o teste de linha mais de uma vez, com intervalo, antes de concluir. Cabo mal encaixado e sinal na zona cinzenta são as causas mais comuns. Pergunte ao cliente se o problema persiste depois de alguns minutos.

## S07 — Sinal igual ou abaixo de -27 dBm
Categoria: sinal fraco.
Sinal igual ou abaixo de -27 dBm é falha física provável: cabo danificado, conector solto ou problema na fibra. Reiniciar a conexão não resolve e não deve ser tentado. Proponha visita técnica para no máximo o dia seguinte e só agende com a confirmação do cliente.

## S08 — Sinal entre -25 e -27 dBm (zona cinzenta)
Categoria: sinal fraco.
Nessa faixa o sinal ainda funciona mas é instável. Rode o teste de linha duas vezes, com intervalo, antes de concluir a causa. Se continuar nessa faixa, trate como possível falha física e explique ao cliente.

## S09 — Queda no bairro inteiro
Categoria: queda coletiva.
Quando o bairro do cliente está em manutenção ou com rompimento de cabo, o problema é coletivo. Não ofereça visita técnica individual: explique que a equipe de rede já está atuando na região e que o serviço volta quando a manutenção terminar.

## S10 — O cliente diz que caiu, mas o teste mostra ONLINE
Categoria: divergência.
Quando o relato do cliente contradiz o teste, não feche o caso como resolvido. Peça ao cliente para testar em outro aparelho, reiniciar o roteador dele e conferir os cabos. Verifique também se o bairro está em manutenção.

## S11 — Luz verde, mas nada abre
Categoria: wi-fi.
Com a conexão verde e sem navegação em nenhum site, o problema costuma estar no roteador do cliente. Peça para reiniciar o roteador e testar de novo.

## S12 — Depois de reiniciar a conexão
Categoria: procedimento.
Depois de reiniciar a conexão remotamente, rode o teste de linha de novo. Só diga que o problema foi resolvido se o novo teste confirmar ONLINE com sinal normal.

## S13 — Cabo de fibra solto ou dobrado
Categoria: sinal fraco.
Cabo encostado por animais ou móveis é causa frequente de sinal fraco. A fibra não pode ser dobrada em ângulo fechado nem puxada. Se o cliente reencaixar o cabo e o sinal voltar ao normal, o caso se resolve sem técnico.

## S14 — Troca de senha do Wi-Fi
Categoria: fora das ferramentas.
Nesta versão o agente não tem ferramenta para trocar a senha do Wi-Fi. Oriente o cliente a seguir o manual do roteador ou ofereça encaminhamento para um atendente humano.
