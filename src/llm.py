import json
import os
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional
from urllib.parse import urlparse

from . import config


class ErroLLMFatal(Exception):
    pass


class ProvedorNaoPermitido(ErroLLMFatal):
    """Controle C2 (docs/seguranca.md): o LLM_BASE_URL aponta para um host
    fora de config.HOSTS_LLM_PERMITIDOS. Levantado ANTES de criar o cliente,
    então a chave de API nunca sai da máquina para esse host (fail-closed)."""


def validar_base_url(base_url: str) -> str:
    """Devolve o host se for permitido; levanta ProvedorNaoPermitido se não.
    http só é aceito para localhost (modelo local); para o resto, só https."""
    alvo = urlparse(base_url or "")
    host = (alvo.hostname or "").lower()
    if host not in config.HOSTS_LLM_PERMITIDOS:
        raise ProvedorNaoPermitido(f"host_nao_permitido:{host or 'vazio'}")
    if alvo.scheme != "https" and host not in ("localhost", "127.0.0.1"):
        raise ProvedorNaoPermitido(f"esquema_nao_permitido:{alvo.scheme}")
    return host


@dataclass
class RespostaLLM:
    content: Optional[str] = None
    tool_calls: List[dict] = field(default_factory=list)  # {id, nome, args}
    tokens: int = 0              # entrada + saída
    tokens_entrada: int = 0
    tokens_saida: int = 0
    erro_argumentos: List[str] = field(default_factory=list)

    @property
    def mensagem(self) -> dict:
        msg = {"role": "assistant", "content": self.content or ""}
        if self.tool_calls:
            msg["tool_calls"] = [
                {
                    "id": c["id"],
                    "type": "function",
                    "function": {"name": c["nome"], "arguments": json.dumps(c["args"], ensure_ascii=False)},
                }
                for c in self.tool_calls
            ]
        return msg


def texto(conteudo: str, tokens: int = 50) -> RespostaLLM:
    return RespostaLLM(content=conteudo, tokens=tokens)


def chamada(nome: str, args: Optional[dict] = None, id: Optional[str] = None, tokens: int = 50) -> RespostaLLM:
    return RespostaLLM(tool_calls=[{"id": id or f"call_{nome}", "nome": nome, "args": args or {}}], tokens=tokens)


def _args_seguros(texto: str, erros: List[str]) -> dict:
    """json.loads dos argumentos sem derrubar o atendimento (devolutiva P1, 6b):
    argumento malformado vira {} e o erro fica registrado."""
    try:
        valor = json.loads(texto or "{}")
        return valor if isinstance(valor, dict) else {}
    except json.JSONDecodeError:
        erros.append((texto or "")[:80])
        return {}


class ClienteLLM:
    def __init__(self, client=None, modelo: str = config.MODELO, esperar: Callable[[float], None] = time.sleep):
        self._client = client
        self.modelo = modelo
        self._esperar = esperar

    def _cliente(self):
        if self._client is None:
            from openai import OpenAI

            base_url = os.environ.get("LLM_BASE_URL", "")
            validar_base_url(base_url)  # C2: recusa antes de a chave sair da máquina
            chave = os.environ.get("OPENAI_API_KEY")
            if not chave:
                raise ErroLLMFatal("OPENAI_API_KEY ausente no .env")
            self._client = OpenAI(base_url=base_url, api_key=chave)
        return self._client

    def chamar(self, mensagens: List[dict], ferramentas: List[dict]) -> RespostaLLM:
        import openai

        recuperaveis = (openai.RateLimitError, openai.APIConnectionError, openai.APITimeoutError)
        cliente = self._cliente()
        for tentativa in range(1, config.TENTATIVAS_LLM + 1):
            try:
                r = cliente.chat.completions.create(
                    model=self.modelo,
                    messages=mensagens,
                    tools=ferramentas,
                    temperature=config.TEMPERATURE,
                    max_tokens=config.MAX_TOKENS_RESPOSTA,
                )
                break
            except recuperaveis as erro:
                if tentativa == config.TENTATIVAS_LLM:
                    raise ErroLLMFatal(f"esgotou {tentativa} tentativas: {type(erro).__name__}") from erro
                self._esperar(2 ** tentativa)
            except Exception as erro:  # autenticação, requisição inválida etc.
                raise ErroLLMFatal(f"{type(erro).__name__}: {erro}") from erro
        msg = r.choices[0].message
        erros: List[str] = []
        chamadas = [
            {"id": c.id, "nome": c.function.name, "args": _args_seguros(c.function.arguments, erros)}
            for c in (msg.tool_calls or [])
        ]
        uso = getattr(r, "usage", None)
        entrada = getattr(uso, "prompt_tokens", 0) or 0
        saida = getattr(uso, "completion_tokens", 0) or 0
        total = getattr(uso, "total_tokens", 0) or (entrada + saida)
        return RespostaLLM(content=msg.content, tool_calls=chamadas, tokens=total,
                           tokens_entrada=entrada, tokens_saida=saida, erro_argumentos=erros)


class LLMSimulado:
    """Roteiro fixo de respostas, para testes e para os scripts que não
    podem chamar o modelo. Cada item é uma RespostaLLM ou uma função
    (mensagens) -> RespostaLLM."""

    modelo = "simulado"

    def __init__(self, roteiro):
        self.roteiro = list(roteiro)
        self.chamadas = 0

    def chamar(self, mensagens, ferramentas):
        self.chamadas += 1
        if not self.roteiro:
            raise ErroLLMFatal("roteiro do LLMSimulado esgotado")
        item = self.roteiro.pop(0)
        if isinstance(item, Exception):
            raise item
        return item(mensagens) if callable(item) else item
