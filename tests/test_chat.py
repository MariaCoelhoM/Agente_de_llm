"""O chatbot: conversa de vários turnos sobre o mesmo checkpoint, e a
aprovação lida pelo código a partir do que o cliente digita."""
import pytest

from src import config, db
from src.chat import Conversa, interpretar_aprovacao
from src.grafo import _janela
from src.llm import LLMSimulado, chamada, texto
from src.modelo_regras import ModeloRegras

from .conftest import AMANHA, HOJE

H = HOJE.isoformat()


def visitas():
    conn = db.conectar()
    linhas = conn.execute("SELECT contrato, data FROM visitas").fetchall()
    conn.close()
    return [tuple(l) for l in linhas]


@pytest.mark.parametrize("texto,esperado", [
    ("sim", {"decisao": "aprovar"}),
    ("Pode sim, obrigado", {"decisao": "aprovar"}),
    ("não, obrigado", {"decisao": "rejeitar"}),
    ("nao quero", {"decisao": "rejeitar"}),
    ("pode ser 2026-10-22", {"decisao": "editar", "data": "2026-10-22"}),
    ("não, prefiro dia 22", {"decisao": "editar", "data": "2026-10-22"}),
    ("dia 5", {"decisao": "editar", "data": "2026-11-05"}),
    ("20/10", {"decisao": "editar", "data": "2026-10-20"}),
    ("depois de amanhã", {"decisao": "editar", "data": "2026-10-20"}),
    ("hmm, quanto custa?", None),
])
def test_interpretar_aprovacao(texto, esperado):
    assert interpretar_aprovacao(texto, H) == esperado


def test_conversa_com_sim_agenda(checkpointer):
    c = Conversa(telefone="+5511900000004", llm=ModeloRegras(), checkpointer=checkpointer)
    r = c.enviar("estou sem internet, a luz está vermelha")
    assert r["tipo"] == "aprovacao" and AMANHA in r["texto"]
    r = c.enviar("sim")
    assert r["tipo"] == "resposta" and visitas() == [("C004", AMANHA)]
    assert "agendada" in r["texto"]


def test_conversa_com_nao_nao_agenda(checkpointer):
    c = Conversa(telefone="+5511900000004", llm=ModeloRegras(), checkpointer=checkpointer)
    c.enviar("sem internet")
    r = c.enviar("não, obrigado")
    assert visitas() == [] and "não agendei" in r["texto"].lower()


def test_resposta_que_nao_e_entendida_pergunta_de_novo_e_depois_rejeita(checkpointer):
    c = Conversa(telefone="+5511900000004", llm=ModeloRegras(), checkpointer=checkpointer)
    c.enviar("sem internet")
    assert c.enviar("hmm")["tipo"] == "aprovacao"
    assert c.enviar("quanto custa?")["tipo"] == "aprovacao"
    r = c.enviar("sei lá")
    assert r["tipo"] == "resposta" and visitas() == []
    assert c.pausas[-1]["resposta"]["motivo"] == "resposta_nao_entendida"


def test_modelo_nao_aprova_a_propria_proposta(checkpointer):
    """A resposta à pausa é lida pelo código; um 'sim' escrito pelo modelo não conta."""
    c = Conversa(contrato="C004", llm=LLMSimulado([
        chamada("testar_linha"), chamada("propor_visita", {"data": AMANHA}),
    ]), checkpointer=checkpointer)
    r = c.enviar("sem internet")
    assert r["tipo"] == "aprovacao" and visitas() == []


def test_segundo_turno_nao_cai_na_triagem_de_entrada_incompleta(checkpointer):
    c = Conversa(contrato="C001", llm=LLMSimulado([texto("Vou testar. Pode me dizer a cor da luz?"),
                                                   texto("Entendi.")]), checkpointer=checkpointer)
    c.enviar("a internet caiu")
    r = c.enviar("sim")  # não descreve sintoma, mas é resposta a uma conversa em andamento
    assert r["motivo"] == "resposta_final"


def test_mesma_conversa_mesmo_thread_e_historico(checkpointer):
    simulado = LLMSimulado([texto("a"), lambda msgs: texto(str(sum(m["role"] == "user" for m in msgs)))])
    c = Conversa(contrato="C001", llm=simulado, checkpointer=checkpointer)
    c.enviar("internet caiu")
    r = c.enviar("e agora?")
    assert r["texto"] == "2"  # o modelo viu as duas mensagens do cliente


def test_janela_corta_em_mensagem_do_cliente(monkeypatch):
    monkeypatch.setattr(config, "JANELA_TURNOS", 2)
    msgs = []
    for i in range(4):
        msgs += [{"role": "user", "content": f"u{i}"},
                 {"role": "assistant", "content": "", "tool_calls": [{"id": f"c{i}"}]},
                 {"role": "tool", "tool_call_id": f"c{i}", "content": "{}"},
                 {"role": "assistant", "content": f"a{i}"}]
    j = _janela(msgs)
    assert j[0] == {"role": "user", "content": "u2"} and len(j) == 8


def test_orcamento_e_por_turno(checkpointer, monkeypatch):
    """Tokens gastos no turno 1 não esgotam o turno 2."""
    monkeypatch.setattr(config, "TETO_TOKENS", 100)
    c = Conversa(contrato="C001", llm=LLMSimulado([texto("a", tokens=90), texto("b", tokens=90)]),
                 checkpointer=checkpointer)
    c.enviar("internet caiu")
    assert c.enviar("e agora?")["motivo"] == "resposta_final"


def test_conversa_longa_transfere(checkpointer, monkeypatch):
    monkeypatch.setattr(config, "MAX_TURNOS_CONVERSA", 2)
    c = Conversa(contrato="C001", llm=LLMSimulado([texto("a"), texto("b")]), checkpointer=checkpointer)
    c.enviar("internet caiu")
    c.enviar("e agora?")
    r = c.enviar("e aí?")
    assert r["motivo"] == "conversa_longa" and r["encerrada"] is True
    assert c.enviar("alô")["tipo"] == "encerrada"


def test_trace_tem_raiz_com_motivo_e_versao(checkpointer, tmp_path):
    import json
    from src import observabilidade as obs
    destino = tmp_path / "t.jsonl"
    obs.redirecionar(str(destino))
    c = Conversa(contrato="C001", llm=ModeloRegras(), checkpointer=checkpointer)
    c.enviar("internet caiu")
    spans = [json.loads(l) for l in destino.read_text(encoding="utf-8").splitlines()]
    raiz = [s for s in spans if s["parent_id"] is None][0]
    assert raiz["nome"] == "invoke_agent suporte_tecnico_domestico"
    assert raiz["atributos"]["app.motivo_termino"] == "resposta_final"
    assert raiz["atributos"]["app.versao_sistema"] == config.VERSAO_SISTEMA
    nomes = {s["nome"] for s in spans}
    assert "chat regras-v1" in nomes and "execute_tool testar_linha" in nomes
    assert all(s["trace_id"] == raiz["trace_id"] for s in spans)
