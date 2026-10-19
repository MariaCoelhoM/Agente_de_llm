"""
Memória de longo prazo do agente (enunciado §5), implementando o que
docs/memoria.md decidiu.

Três memórias, cada uma na estrutura que o padrão de acesso pede:
  semântica  -> chave-valor por contrato (tabela `semantica`), lida por chave
  episódica  -> um resumo por atendimento (tabela `episodica`), recuperada por
                similaridade lexical dentro do contrato
  procedural -> texto curado em src/prompts/procedural.md, sempre no prompt

Quem escreve: o CÓDIGO, por regra, depois do atendimento, a partir do que as
ferramentas retornaram. O modelo nunca decide o que vira memória, e nada que
o cliente apenas afirmou vira fato.

Três causas de esquecimento, todas implementadas:
  contradição -> fato com vigente_desde mais recente vence; o perdedor é
                 registrado em `descartes`
  decaimento  -> episódio com mais de DECAIMENTO_DIAS é rebaixado (ativo=0),
                 não apagado
  remoção     -> remover_titular apaga o contrato de todas as estruturas; a
                 verificação é feita por outro programa (scripts/varrer_contrato.py)
"""
import datetime
import hashlib
import json
import os
import sqlite3
from typing import Dict, List, Optional

from . import config, rag

GLOBAL = "*"


def _conectar(caminho: Optional[str] = None) -> sqlite3.Connection:
    caminho = caminho or config.CAMINHO_MEMORIA
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    conn = sqlite3.connect(caminho)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS semantica (
            chave_idem TEXT PRIMARY KEY,
            contrato TEXT NOT NULL,
            chave TEXT NOT NULL,
            valor TEXT NOT NULL,
            vigente_desde TEXT NOT NULL,
            origem TEXT NOT NULL,
            registrado_em TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS descartes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contrato TEXT NOT NULL,
            chave TEXT NOT NULL,
            valor_descartado TEXT NOT NULL,
            vigente_desde_descartado TEXT NOT NULL,
            superado_por_valor TEXT NOT NULL,
            superado_por_desde TEXT NOT NULL,
            registrado_em TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS episodica (
            chave_idem TEXT PRIMARY KEY,
            contrato TEXT NOT NULL,
            data TEXT NOT NULL,
            sintoma TEXT NOT NULL,
            causa TEXT NOT NULL,
            acao TEXT NOT NULL,
            resultado TEXT NOT NULL,
            texto TEXT NOT NULL,
            ativo INTEGER NOT NULL DEFAULT 1
        );
        """
    )
    return conn


def _chave(*partes: str) -> str:
    return hashlib.sha256("|".join(partes).encode("utf-8")).hexdigest()[:16]


def _agora() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


# --------------------------------------------------------------------------
# semântica
# --------------------------------------------------------------------------

def gravar_fato(
    contrato: str,
    chave: str,
    valor: str,
    vigente_desde: str,
    origem: str,
    caminho: Optional[str] = None,
) -> dict:
    """Idempotente: a chave deriva do conteúdo (contrato, chave, valor, data).
    Se um fato mais novo contradiz o vigente, o antigo vai para `descartes`."""
    chave_idem = _chave(contrato, chave, valor, vigente_desde)
    conn = _conectar(caminho)
    try:
        existente = conn.execute(
            "SELECT 1 FROM semantica WHERE chave_idem = ?", (chave_idem,)
        ).fetchone()
        if existente:
            return {"chave_idem": chave_idem, "ja_existia": True}
        atual = _fato_vigente(conn, contrato, chave, vigente_desde)
        conn.execute(
            "INSERT INTO semantica VALUES (?,?,?,?,?,?,?)",
            (chave_idem, contrato, chave, valor, vigente_desde, origem, _agora()),
        )
        if atual and atual["valor"] != valor and atual["vigente_desde"] < vigente_desde:
            conn.execute(
                "INSERT INTO descartes (contrato, chave, valor_descartado, "
                "vigente_desde_descartado, superado_por_valor, superado_por_desde, "
                "registrado_em) VALUES (?,?,?,?,?,?,?)",
                (contrato, chave, atual["valor"], atual["vigente_desde"], valor,
                 vigente_desde, _agora()),
            )
        conn.commit()
        return {"chave_idem": chave_idem, "ja_existia": False}
    finally:
        conn.close()


def _fato_vigente(conn, contrato: str, chave: str, data: str) -> Optional[sqlite3.Row]:
    """max(vigente_desde) entre os fatos com vigente_desde <= data. Empate de
    data: vence o registrado por último. Regra puramente de data: o modelo
    nunca escolhe entre dois fatos."""
    return conn.execute(
        "SELECT valor, vigente_desde FROM semantica "
        "WHERE contrato = ? AND chave = ? AND vigente_desde <= ? "
        "ORDER BY vigente_desde DESC, registrado_em DESC LIMIT 1",
        (contrato, chave, data),
    ).fetchone()


def fato_vigente(
    contrato: str, chave: str, data: str, caminho: Optional[str] = None
) -> Optional[Dict[str, str]]:
    conn = _conectar(caminho)
    try:
        linha = _fato_vigente(conn, contrato, chave, data)
        return dict(linha) if linha else None
    finally:
        conn.close()


def listar_descartes(contrato: str, caminho: Optional[str] = None) -> List[dict]:
    conn = _conectar(caminho)
    try:
        return [
            dict(l)
            for l in conn.execute(
                "SELECT * FROM descartes WHERE contrato = ? ORDER BY id", (contrato,)
            )
        ]
    finally:
        conn.close()


# --------------------------------------------------------------------------
# episódica
# --------------------------------------------------------------------------

def registrar_episodio(
    contrato: str,
    data: str,
    sintoma: str,
    causa: str,
    acao: str,
    resultado: str,
    caminho: Optional[str] = None,
) -> dict:
    sintoma = " ".join(sintoma.split())[:200]
    chave_idem = _chave(contrato, data, sintoma, causa, acao, resultado)
    texto = f"{sintoma}. causa: {causa}. ação: {acao}. resultado: {resultado}."
    conn = _conectar(caminho)
    try:
        existente = conn.execute(
            "SELECT 1 FROM episodica WHERE chave_idem = ?", (chave_idem,)
        ).fetchone()
        if existente:
            return {"chave_idem": chave_idem, "ja_existia": True}
        conn.execute(
            "INSERT INTO episodica VALUES (?,?,?,?,?,?,?,?,1)",
            (chave_idem, contrato, data, sintoma, causa, acao, resultado, texto),
        )
        conn.commit()
        return {"chave_idem": chave_idem, "ja_existia": False}
    finally:
        conn.close()


def buscar_episodios(
    contrato: str,
    sintoma: str,
    hoje: str,
    n: int = config.MEMORIA_EPISODIOS_MAX,
    caminho: Optional[str] = None,
) -> List[dict]:
    """Filtra por contrato exato e por episódios ativos, depois ordena por
    similaridade lexical do sintoma. Sem sobreposição de palavras, cai para o
    mais recente: o histórico do próprio cliente ainda é relevante mesmo que
    ele descreva o problema com outras palavras."""
    conn = _conectar(caminho)
    try:
        linhas = [
            dict(l)
            for l in conn.execute(
                "SELECT * FROM episodica WHERE contrato = ? AND ativo = 1 "
                "ORDER BY data DESC",
                (contrato,),
            )
        ]
    finally:
        conn.close()
    if not linhas:
        return []
    trechos = [
        rag.Trecho(l["chave_idem"], "episodica", "", l["texto"], True, "cliente")
        for l in linhas
    ]
    pontos = rag.Indice(trechos).pontuar(rag.tokenizar(sintoma))
    ordenados = sorted(
        zip(linhas, pontos), key=lambda par: (par[1], par[0]["data"]), reverse=True
    )
    return [l for l, _ in ordenados[:n]]


def aplicar_decaimento(
    hoje: str,
    dias: int = config.DECAIMENTO_DIAS,
    caminho: Optional[str] = None,
) -> int:
    """Rebaixa (ativo=0) os episódios mais velhos que `dias`. Não apaga:
    o histórico completo continua arquivado, só sai da janela do agente."""
    limite = (datetime.date.fromisoformat(hoje) - datetime.timedelta(days=dias)).isoformat()
    conn = _conectar(caminho)
    try:
        cur = conn.execute(
            "UPDATE episodica SET ativo = 0 WHERE ativo = 1 AND data < ?", (limite,)
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


# --------------------------------------------------------------------------
# procedural
# --------------------------------------------------------------------------

def carregar_procedural() -> str:
    caminho = os.path.join(config.PASTA_PROMPTS, config.PROMPT_PROCEDURAL)
    with open(caminho, encoding="utf-8") as arquivo:
        return arquivo.read().strip()


# --------------------------------------------------------------------------
# política de escrita: o código extrai, o modelo não decide
# --------------------------------------------------------------------------

def extrair_episodio(mensagem_inicial: str, trajetoria: List[dict]) -> Dict[str, str]:
    """Regras fixas sobre o que as ferramentas retornaram."""
    chamadas = [t for t in trajetoria if t.get("tipo") == "ferramenta"]
    testes = [c["resultado"] for c in chamadas if c["nome"] == "testar_linha"
              and "erro" not in c["resultado"]]
    bairros = [c["resultado"] for c in chamadas if c["nome"] == "conferir_queda_bairro"
               and "erro" not in c["resultado"]]
    reiniciou = any(c["nome"] == "reiniciar_conexao" and "erro" not in c["resultado"]
                    for c in chamadas)
    aprovacoes = [t for t in trajetoria if t.get("tipo") == "aprovacao_humana"]
    agendou = any(a.get("decisao") in ("aprovar", "editar") and "erro" not in a.get("resultado", {})
                  for a in aprovacoes)

    if bairros and bairros[-1].get("em_manutencao"):
        causa = "bairro_em_manutencao"
    elif testes and testes[-1].get("falha_fisica_provavel"):
        causa = "falha_fisica"
    elif reiniciou:
        causa = "sinal_recuperavel_por_reinicio"
    elif testes:
        causa = "sem_causa_identificada"
    else:
        causa = "nao_diagnosticado"

    if agendou:
        acao, resultado = "agendou_visita", "agendado"
    elif reiniciou and testes and testes[-1].get("status") == "ONLINE":
        acao, resultado = "reiniciou_conexao", "resolvido"
    elif any(t.get("tipo") == "transbordo" for t in trajetoria):
        acao, resultado = "encaminhou_humano", "escalado"
    elif aprovacoes:
        acao, resultado = "visita_nao_agendada", "aberto"
    else:
        acao, resultado = "nenhuma", "aberto"
    return {"sintoma": mensagem_inicial, "causa": causa, "acao": acao, "resultado": resultado}


def gravar_atendimento(
    contrato: str,
    hoje: str,
    mensagem_inicial: str,
    trajetoria: List[dict],
    caminho: Optional[str] = None,
) -> dict:
    """Chamada uma vez, ao fim do atendimento. O que passa da conversa para a
    memória de longo prazo é isto e nada mais: um episódio e, se uma
    ferramenta mediu o sinal, o último sinal conhecido."""
    ep = extrair_episodio(mensagem_inicial, trajetoria)
    saida = {"episodio": registrar_episodio(contrato, hoje, caminho=caminho, **ep)}
    testes = [t for t in trajetoria if t.get("tipo") == "ferramenta"
              and t["nome"] == "testar_linha" and "erro" not in t["resultado"]]
    if testes:
        saida["fato"] = gravar_fato(
            contrato, "ultimo_sinal_dbm", str(testes[-1]["resultado"]["sinal_dbm"]),
            hoje, "testar_linha", caminho,
        )
    return saida


# --------------------------------------------------------------------------
# contexto entregue ao modelo, com orçamento
# --------------------------------------------------------------------------

def estimar_tokens(texto: str) -> int:
    return (len(texto) + 3) // 4


def montar_contexto(
    contrato: str,
    sintoma: str,
    hoje: str,
    orcamento_tokens: int = config.ORCAMENTO_TOKENS["memoria_longo_prazo"],
    caminho: Optional[str] = None,
) -> str:
    """Bloco de memória de longo prazo. Se estourar o orçamento, corta o
    episódio mais antigo primeiro (ordem de descarte do docs/memoria.md §1.2)."""
    if not os.path.exists(caminho or config.CAMINHO_MEMORIA):
        return ""
    fato = fato_vigente(contrato, "ultimo_sinal_dbm", hoje, caminho)
    episodios = buscar_episodios(contrato, sintoma, hoje, caminho=caminho)
    if not fato and not episodios:
        return ""

    def renderizar(eps: List[dict]) -> str:
        linhas = ["Histórico deste cliente (memória do sistema, não confirmado pelo cliente agora):"]
        if fato:
            linhas.append(f"- último sinal medido: {fato['valor']} dBm em {fato['vigente_desde']}")
        for e in eps:
            linhas.append(
                f"- {e['data']}: relato \"{e['sintoma']}\"; causa {e['causa']}; "
                f"ação {e['acao']}; resultado {e['resultado']}"
            )
        return "\n".join(linhas)

    por_data = sorted(episodios, key=lambda e: e["data"])  # mais antigo primeiro
    while por_data and estimar_tokens(renderizar(por_data)) > orcamento_tokens:
        por_data.pop(0)
    if not por_data and not fato:
        return ""
    return renderizar(por_data)


# --------------------------------------------------------------------------
# remoção em todas as estruturas
# --------------------------------------------------------------------------

def remover_titular(
    contrato: str,
    caminho_memoria: Optional[str] = None,
    caminho_checkpoints: Optional[str] = None,
    pasta_logs: Optional[str] = None,
) -> Dict[str, int]:
    """Apaga o contrato de: semântica, descartes, episódica, checkpoints e
    logs. Não toca no provedor.db (fonte de verdade do provedor, fora da
    memória do agente) nem em backups externos. Quem confere é outro
    programa: scripts/varrer_contrato.py."""
    removidos: Dict[str, int] = {}
    conn = _conectar(caminho_memoria)
    try:
        for tabela in ("semantica", "descartes", "episodica"):
            cur = conn.execute(f"DELETE FROM {tabela} WHERE contrato = ?", (contrato,))
            removidos[tabela] = cur.rowcount
        conn.commit()
    finally:
        conn.close()

    caminho_cp = caminho_checkpoints or config.CAMINHO_CHECKPOINTS
    removidos["checkpoints"] = 0
    if os.path.exists(caminho_cp):
        conn = sqlite3.connect(caminho_cp)
        try:
            for tabela in ("checkpoints", "writes"):
                try:
                    cur = conn.execute(
                        f"DELETE FROM {tabela} WHERE thread_id LIKE ?", (f"{contrato}:%",)
                    )
                    removidos["checkpoints"] += cur.rowcount
                except sqlite3.OperationalError:
                    pass
            conn.commit()
        finally:
            conn.close()

    pasta = pasta_logs or config.PASTA_LOGS
    removidos["logs"] = 0
    if os.path.isdir(pasta):
        for nome in os.listdir(pasta):
            if not nome.endswith(".json"):
                continue
            caminho = os.path.join(pasta, nome)
            try:
                with open(caminho, encoding="utf-8") as arquivo:
                    registro = json.load(arquivo)
            except (OSError, json.JSONDecodeError):
                continue
            if registro.get("contrato") == contrato:
                os.remove(caminho)
                removidos["logs"] += 1
    return removidos
