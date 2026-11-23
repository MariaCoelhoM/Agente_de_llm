"""
Atendimento de uma mensagem só (a interface da Parte 2), mantida para os
scripts de demonstração e os testes. Por dentro, usa a mesma `Conversa` do
chat (src/chat.py): um turno, e as pausas de aprovação respondidas por um
`decisor`. Para conversar com o agente, use `python -m src.chat`.

  python -m src.agent C001 "minha internet caiu"
  python -m src.agent C004 "sem internet" --decisao editar --data 2026-11-20
"""
import argparse
import threading
from typing import Callable, Optional

from . import config, db
from .chat import Conversa, cartao_aprovacao, prompts_em_uso  # noqa: F401  (prompts_em_uso: compatibilidade)


def decisor_terminal(payload: dict) -> dict:
    print("\n=== APROVAÇÃO NECESSÁRIA ===")
    print(cartao_aprovacao(payload))
    print("Opções: aprovar | rejeitar | editar AAAA-MM-DD")
    caixa = {}

    def ler():
        caixa["texto"] = input("> ").strip()

    t = threading.Thread(target=ler, daemon=True)
    t.start()
    t.join(payload["prazo_segundos"])
    if "texto" not in caixa:
        print("\n(prazo esgotado)")
        return {"decisao": "expirou"}
    partes = caixa["texto"].split()
    if partes and partes[0] == "editar" and len(partes) > 1:
        return {"decisao": "editar", "data": partes[1]}
    return {"decisao": partes[0] if partes else "rejeitar"}


def decisor_fixo(decisao: str, data: Optional[str] = None) -> Callable[[dict], dict]:
    def decidir(payload):
        return {"decisao": decisao, **({"data": data} if data else {})}
    return decidir


def executar_atendimento(
    contrato: str,
    mensagem: str,
    llm=None,
    decisor: Callable[[dict], dict] = decisor_terminal,
    checkpointer=None,
    pasta_logs: Optional[str] = None,
    rotulo: Optional[str] = None,
) -> dict:
    conversa = Conversa(contrato=contrato, llm=llm, checkpointer=checkpointer,
                        pasta_logs=pasta_logs, rotulo=rotulo or f"caso_{contrato}")
    try:
        r = conversa.enviar(mensagem)
        while r["tipo"] == "aprovacao":
            r = conversa.decidir(decisor(conversa.pendente))
        registro = conversa.registro()
        registro["arquivo_log"] = conversa.arquivo_log
        return registro
    finally:
        conversa.fechar()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("contrato")
    p.add_argument("mensagem", nargs="?", default="Minha internet caiu.")
    p.add_argument("--decisao", choices=["aprovar", "rejeitar", "editar", "expirou"])
    p.add_argument("--data")
    p.add_argument("--rotulo")
    a = p.parse_args()
    db.inicializar()
    decisor = decisor_fixo(a.decisao, a.data) if a.decisao else decisor_terminal
    r = executar_atendimento(a.contrato, a.mensagem, decisor=decisor, rotulo=a.rotulo)
    print(f"\nResposta: {r['saida']['resultado']}")
    print(f"Fontes: {[f['id'] for f in r['saida']['fontes']]}  suficiente={r['saida']['suficiente']}")
    print(f"Parou por: {r['motivo_parada']}   Log: {r['arquivo_log']}")


if __name__ == "__main__":
    main()
