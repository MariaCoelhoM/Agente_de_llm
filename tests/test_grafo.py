import json
import sqlite3

import pytest

from src import config, db, llm, tools
from src.agent import decisor_fixo, executar_atendimento
from src.llm import LLMSimulado, chamada, texto

from .conftest import AMANHA


def rodar(contrato, mensagem, roteiro, checkpointer, decisao=None, data=None):
    simulado = LLMSimulado(roteiro)
    decisor = decisor_fixo(decisao, data) if decisao else decisor_fixo("rejeitar")
    r = executar_atendimento(contrato, mensagem, llm=simulado, decisor=decisor,
                             checkpointer=checkpointer, rotulo="teste")
    return r, simulado


def visitas():
    conn = db.conectar()
    linhas = conn.execute("SELECT contrato, data, status FROM visitas").fetchall()
    conn.close()
    return [tuple(l) for l in linhas]


def roteiro_visita(final):
    return [
        chamada("testar_linha"),
        chamada("obter_data_atual"),
        chamada("propor_visita", {"data": AMANHA}),
        texto(final),
    ]


def test_caminho_feliz_reinicia_e_confirma(checkpointer):
    r, _ = rodar("C001", "luz vermelha piscando", [
        chamada("testar_linha"), chamada("reiniciar_conexao"), chamada("testar_linha"),
        texto("Reiniciei e a linha voltou ONLINE."),
    ], checkpointer)
    assert r["motivo_parada"] == "resposta_final"
    assert r["saida"]["suficiente"] is True
    assert {"testar_linha", "reiniciar_conexao"} <= {f["id"] for f in r["saida"]["fontes"]}
    assert visitas() == []


def test_aprovar_agenda_uma_visita(checkpointer):
    r, _ = rodar("C004", "sem internet", roteiro_visita("Visita agendada."), checkpointer, "aprovar")
    assert visitas() == [("C004", AMANHA, "AGENDADA")]
    assert r["pausas_de_aprovacao"][0]["payload"]["data_proposta"] == AMANHA
    assert "agendar_visita_tecnico" in {f["id"] for f in r["saida"]["fontes"]}


def test_rejeitar_nao_agenda(checkpointer):
    r, _ = rodar("C004", "sem internet", roteiro_visita("Não agendei."), checkpointer, "rejeitar")
    assert visitas() == []
    assert r["motivo_parada"] == "resposta_final"


def test_editar_agenda_na_data_escolhida(checkpointer):
    r, _ = rodar("C004", "sem internet", roteiro_visita("Agendada."), checkpointer,
                 "editar", "2026-10-22")
    assert visitas() == [("C004", "2026-10-22", "AGENDADA")]


@pytest.mark.parametrize("data", ["2026-10-01", "2026-12-31", "amanhã"])
def test_edicao_invalida_vira_rejeicao(checkpointer, data):
    rodar("C004", "sem internet", roteiro_visita("Não agendei."), checkpointer, "editar", data)
    assert visitas() == []


def test_expirar_nao_agenda_e_encaminha_humano(checkpointer):
    # o roteiro tem só 3 respostas: depois do prazo o modelo nem é chamado de novo
    r, simulado = rodar("C004", "sem internet", roteiro_visita("x")[:3], checkpointer, "expirou")
    assert visitas() == []
    assert r["motivo_parada"] == "aprovacao_expirada"
    assert r["saida"]["encaminhar_humano"] is True
    assert simulado.chamadas == 3


def test_aprovacao_repetida_nao_duplica(checkpointer):
    rodar("C004", "sem internet", roteiro_visita("ok"), checkpointer, "aprovar")
    rodar("C004", "sem internet de novo", roteiro_visita("ok"), checkpointer, "aprovar")
    assert len(visitas()) == 1


def test_modelo_nao_tem_ferramenta_que_agenda():
    nomes = {f["function"]["name"] for f in tools.FERRAMENTAS_OPENAI}
    assert "agendar_visita_tecnico" not in nomes
    assert "agendar_visita_tecnico" not in tools.FUNCOES


def test_modelo_chamando_agendar_por_fora_nao_agenda(checkpointer):
    r, _ = rodar("C004", "sem internet", [
        chamada("agendar_visita_tecnico", {"data": AMANHA, "confirmado_pelo_cliente": True}),
        texto("Tentei."),
    ], checkpointer)
    assert visitas() == []
    t = [x for x in r["trajetoria"] if x.get("nome") == "agendar_visita_tecnico"][0]
    assert t["resultado"]["erro"] == "ferramenta_desconhecida"


def test_propor_sem_testar_linha_e_recusado(checkpointer):
    r, _ = rodar("C004", "sem internet", [
        chamada("propor_visita", {"data": AMANHA}), texto("Não consegui."),
    ], checkpointer, "aprovar")
    assert visitas() == []
    assert r["pausas_de_aprovacao"] == []


def test_bairro_em_manutencao_nao_chega_na_aprovacao(checkpointer):
    r, _ = rodar("C005", "sem internet", [
        chamada("testar_linha"), chamada("propor_visita", {"data": AMANHA}),
        texto("Há manutenção no seu bairro."),
    ], checkpointer, "aprovar")
    assert visitas() == []
    assert r["pausas_de_aprovacao"] == []


def test_contrato_da_sessao_vence_o_que_o_modelo_digita(checkpointer):
    r, _ = rodar("C001", "sem internet", [chamada("testar_linha", {"contrato": "C004"}), texto("ok")], checkpointer)
    t = [x for x in r["trajetoria"] if x.get("nome") == "testar_linha"][0]
    assert t["resultado"]["contrato"] == "C001"
    assert t["contrato_sobrescrito"] == "C004"


@pytest.mark.parametrize("mensagem", ["oi", "não funciona", "preciso de ajuda"])
def test_entrada_sem_sintoma_pede_detalhes_sem_chamar_o_modelo(checkpointer, mensagem):
    r, simulado = rodar("C001", mensagem, [], checkpointer)
    assert simulado.chamadas == 0
    assert r["motivo_parada"] == "entrada_incompleta"
    assert r["saida"]["suficiente"] is False
    assert r["saida"]["encaminhar_humano"] is False
    assert "luz do modem" in r["saida"]["resultado"]
    assert visitas() == []


def test_entrada_com_sintoma_segue_para_o_modelo(checkpointer):
    r, simulado = rodar("C001", "a luz está vermelha", [texto("Vou verificar. [S01]")], checkpointer)
    assert simulado.chamadas == 1
    assert r["motivo_parada"] != "entrada_incompleta"


def test_cobranca_vai_para_humano_sem_chamar_o_modelo(checkpointer):
    r, simulado = rodar("C001", "quero desconto na fatura", [], checkpointer)
    assert simulado.chamadas == 0
    assert r["saida"]["encaminhar_humano"] is True
    assert r["saida"]["suficiente"] is False


def test_pergunta_fora_do_corpus_recusa_em_codigo(checkpointer):
    r, _ = rodar("C001", "quanto custa o plano de 500 mega de internet", [
        chamada("consultar_base_conhecimento", {"pergunta": "quanto custa o plano de 500 mega de internet"}),
        texto("O plano de 500 mega custa R$ 99,90."),
    ], checkpointer)
    assert r["saida"]["suficiente"] is False
    assert r["saida"]["motivo_insuficiencia"] == "fora_do_corpus"
    assert "99,90" not in r["saida"]["resultado"]


def test_citacao_valida_entra_nas_fontes(checkpointer):
    r, _ = rodar("C001", "o que significa luz vermelha piscando", [
        chamada("consultar_base_conhecimento", {"pergunta": "o que significa a luz vermelha piscando no meu modem"}),
        texto("É perda de sinal da fibra [S01]."),
    ], checkpointer)
    assert r["saida"]["suficiente"] is True
    assert ("corpus", "S01") in {(f["tipo"], f["id"]) for f in r["saida"]["fontes"]}


def test_citacao_inventada_e_detectada(checkpointer):
    r, _ = rodar("C001", "o que significa luz vermelha piscando", [
        chamada("consultar_base_conhecimento", {"pergunta": "o que significa a luz vermelha piscando no meu modem"}),
        texto("Veja [S99]."),
    ], checkpointer)
    assert r["saida"]["citacoes_invalidas"] == ["S99"]
    assert r["saida"]["suficiente"] is False


def test_laco_e_detectado(checkpointer):
    r, _ = rodar("C001", "sem internet", [chamada("conferir_queda_bairro")] * 4, checkpointer)
    assert r["motivo_parada"] == "laco_detectado"
    assert r["saida"]["encaminhar_humano"] is True


def test_limite_de_voltas(checkpointer, monkeypatch):
    monkeypatch.setattr(config, "MAX_VOLTAS_AGENTE", 2)
    r, _ = rodar("C001", "sem internet", [chamada("obter_data_atual"), chamada("conferir_queda_bairro"),
                                chamada("testar_linha")], checkpointer)
    assert r["motivo_parada"] == "limite_de_voltas"


def test_limite_de_tokens(checkpointer, monkeypatch):
    monkeypatch.setattr(config, "TETO_TOKENS", 100)
    r, _ = rodar("C001", "sem internet", [chamada("obter_data_atual", tokens=500), texto("x")], checkpointer)
    assert r["motivo_parada"] == "tokens_esgotados"


def test_erro_fatal_do_modelo_encaminha_humano(checkpointer):
    r, _ = rodar("C001", "sem internet", [llm.ErroLLMFatal("chave invalida")], checkpointer)
    assert r["motivo_parada"] == "erro_fatal_llm"
    assert r["saida"]["encaminhar_humano"] is True


def test_recursion_limit_vira_motivo_de_termino(checkpointer, monkeypatch):
    monkeypatch.setattr(config, "RECURSION_LIMIT", 6)
    r, _ = rodar("C001", "sem internet", [chamada("obter_data_atual"), chamada("conferir_queda_bairro"),
                                chamada("testar_linha"), texto("x")], checkpointer)
    assert r["motivo_parada"] == "recursion_limit"


def test_log_e_gravado_com_campos_do_enunciado(checkpointer, tmp_path):
    rodar("C001", "sem internet", [texto("Olá.")], checkpointer)
    import os
    caminho = os.path.join(config.PASTA_LOGS, "teste.json")
    log = json.load(open(caminho, encoding="utf-8"))
    for campo in ("timestamp", "commit", "modelo", "temperature", "thread_id", "trajetoria", "motivo_parada", "saida"):
        assert campo in log


def test_limite_de_testes_de_linha(checkpointer):
    """A quarta chamada a testar_linha no mesmo atendimento é recusada.
    As escritas (reiniciar) entre os testes evitam o detector de laço."""
    seq = []
    for i in range(3):
        seq += [{"id": f"t{i}", "nome": "testar_linha", "args": {}},
                {"id": f"r{i}", "nome": "reiniciar_conexao", "args": {}}]
    seq.append({"id": "t3", "nome": "testar_linha", "args": {}})
    r, _ = rodar("C001", "sem internet", [llm.RespostaLLM(tool_calls=seq), texto("ok")], checkpointer)
    testes = [t for t in r["trajetoria"] if t.get("nome") == "testar_linha"]
    assert len(testes) == 4
    assert testes[3]["resultado"]["erro"] == "limite_de_testes_atingido"
    assert all("erro" not in t["resultado"] for t in testes[:3])