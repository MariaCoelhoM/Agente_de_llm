import math
import os
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional

from . import config

_STOPWORDS = {
    "a", "o", "as", "os", "um", "uma", "uns", "umas", "de", "do", "da", "dos",
    "das", "em", "no", "na", "nos", "nas", "por", "para", "com", "sem", "e",
    "ou", "que", "se", "ao", "aos", "ser", "estar", "esta", "esse", "essa",
    "isso", "meu", "minha", "seu", "sua", "qual", "quais", "quando", "como",
    "onde", "quanto", "quantos", "quantas", "pode", "posso", "devo", "ja",
    "mais", "muito", "ha", "foi", "sao", "tem", "ter", "fazer", "faz", "eu",
    "me", "te", "lhe", "mas", "ate", "entre", "sobre", "apos", "vez", "vezes",
}


def _sem_acento(texto: str) -> str:
    normal = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in normal if not unicodedata.combining(c))


def _radical(palavra: str) -> str:
    """Remoção mínima de plural. Não é um stemmer completo, e isso é uma
    limitação declarada em docs/rag.md."""
    if len(palavra) > 4 and palavra.endswith("s"):
        return palavra[:-1]
    return palavra


def tokenizar(texto: str) -> List[str]:
    texto = _sem_acento(texto.lower())
    palavras = re.findall(r"[a-z0-9]+", texto)
    return [_radical(p) for p in palavras if p not in _STOPWORDS]


@dataclass
class Trecho:
    id: str
    doc: str
    titulo: str
    texto: str
    vigente: bool
    agente_aplicavel: str

    def como_dict(self) -> dict:
        return {"id": self.id, "doc": self.doc, "titulo": self.titulo, "texto": self.texto}


def _ler_frontmatter(conteudo: str):
    if not conteudo.startswith("---"):
        return {}, conteudo
    partes = conteudo.split("---", 2)
    meta = {}
    for linha in partes[1].strip().splitlines():
        if ":" in linha:
            chave, valor = linha.split(":", 1)
            meta[chave.strip()] = valor.strip()
    return meta, partes[2]


def carregar_trechos(pasta: str = config.PASTA_CORPUS) -> List[Trecho]:
    trechos: List[Trecho] = []
    if not os.path.isdir(pasta):
        return trechos
    for nome in sorted(os.listdir(pasta)):
        if not nome.endswith(".md"):
            continue
        with open(os.path.join(pasta, nome), encoding="utf-8") as arquivo:
            meta, corpo = _ler_frontmatter(arquivo.read())
        doc = meta.get("doc", nome[:-3])
        titulo_doc = meta.get("titulo", doc)
        vigente = meta.get("vigente", "true").lower() == "true"
        agente = meta.get("agente_aplicavel", "cliente")
        for bloco in re.split(r"^## ", corpo, flags=re.MULTILINE)[1:]:
            cabecalho, _, texto = bloco.partition("\n")
            id_item, _, titulo_item = cabecalho.partition("—")
            id_item = id_item.strip()
            titulo_item = titulo_item.strip()
            completo = f"{titulo_doc}. {id_item} — {titulo_item}. {texto.strip()}"
            trechos.append(Trecho(id_item, doc, titulo_item, completo, vigente, agente))
    return trechos


class Indice:
    """BM25 em memória. k1 e b são os valores clássicos; com dezenas de
    trechos não há dado para ajustá-los, então não fingimos que foram
    ajustados."""

    def __init__(self, trechos: List[Trecho], k1: float = 1.5, b: float = 0.75):
        self.trechos = trechos
        self.k1 = k1
        self.b = b
        self._tokens = [tokenizar(t.texto) for t in trechos]
        self._tf = [Counter(tokens) for tokens in self._tokens]
        self._comprimentos = [len(tokens) for tokens in self._tokens]
        total = len(trechos) or 1
        self._media = sum(self._comprimentos) / total
        df: Counter = Counter()
        for contagem in self._tf:
            df.update(contagem.keys())
        self._idf: Dict[str, float] = {
            termo: math.log(1 + (total - n + 0.5) / (n + 0.5)) for termo, n in df.items()
        }

    def pontuar(self, termos: List[str]) -> List[float]:
        pontos = []
        for i, contagem in enumerate(self._tf):
            soma = 0.0
            for termo in set(termos):
                f = contagem.get(termo, 0)
                if not f:
                    continue
                norma = 1 - self.b + self.b * self._comprimentos[i] / (self._media or 1)
                soma += self._idf.get(termo, 0.0) * f * (self.k1 + 1) / (f + self.k1 * norma)
            pontos.append(soma)
        return pontos

    def buscar(self, pergunta: str, k: int = config.RAG_K) -> List[dict]:
        termos = tokenizar(pergunta)
        if not termos:
            return []
        pontos = self.pontuar(termos)
        ordem = sorted(range(len(pontos)), key=lambda i: pontos[i], reverse=True)[:k]
        achados = []
        unicos = set(termos)
        for i in ordem:
            if pontos[i] <= 0:
                continue
            presentes = unicos & set(self._tokens[i])
            achados.append(
                {
                    "trecho": self.trechos[i],
                    "score": round(pontos[i], 3),
                    "cobertura": round(len(presentes) / len(unicos), 3),
                }
            )
        return achados


def construir_indice(
    pasta: str = config.PASTA_CORPUS,
    incluir_revogados: bool = False,
    agente: str = "cliente",
) -> Indice:
    """O filtro de vigência e de agente é aplicado aqui, em código, e não
    pedido ao modelo."""
    trechos = [
        t
        for t in carregar_trechos(pasta)
        if t.agente_aplicavel == agente and (t.vigente or incluir_revogados)
    ]
    return Indice(trechos)


_indice_padrao: Optional[Indice] = None


def obter_indice() -> Indice:
    global _indice_padrao
    if _indice_padrao is None:
        _indice_padrao = construir_indice()
    return _indice_padrao


def consultar_base_conhecimento(pergunta: str, indice: Optional[Indice] = None) -> dict:
    """Ferramenta do agente (leitura). Portão de suficiência em código: se o
    melhor trecho não cobre pelo menos RAG_COBERTURA_MINIMA dos termos da
    pergunta, devolve suficiente=False e nenhum trecho. O modelo recebe a
    recusa como dado e não tem trecho para citar."""
    indice = indice or obter_indice()
    achados = indice.buscar(pergunta, k=config.RAG_K)
    if not achados or achados[0]["cobertura"] < config.RAG_COBERTURA_MINIMA:
        return {
            "suficiente": False,
            "motivo": "nada_relevante_no_corpus",
            "trechos": [],
        }
    return {
        "suficiente": True,
        "trechos": [
            {**a["trecho"].como_dict(), "score": a["score"], "cobertura": a["cobertura"]}
            for a in achados
            if a["cobertura"] >= config.RAG_COBERTURA_MINIMA
        ],
    }
