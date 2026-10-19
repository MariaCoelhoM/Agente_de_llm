import json
import os
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from . import config


class ErroLLMFatal(Exception):
    pass


@dataclass
class RespostaLLM:
    content: Optional[str] = None
    tool_calls: List[dict] = field(default_factory=list)  # {id, nome, args}
    tokens: int = 0

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


class ClienteLLM:
    def __init__(self, client=None, modelo: str = config.MODELO, esperar: Callable[[float], None] = time.sleep):
        self._client = client
        self.modelo = modelo
        self._esperar = esperar

    def _cliente(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(base_url=os.environ["LLM_BASE_URL"], api_key=os.environ["OPENAI_API_KEY"])
        return self._client

    def chamar(self, mensagens: List[dict], ferramentas: List[dict]) -> RespostaLLM:
        import openai

        recuperaveis = (openai.RateLimitError, openai.APIConnectionError, openai.APITimeoutError)
        for tentativa in range(1, config.TENTATIVAS_LLM + 1):
            try:
                r = self._cliente().chat.completions.create(
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
        chamadas = [
            {"id": c.id, "nome": c.function.name, "args": json.loads(c.function.arguments or "{}")}
            for c in (msg.tool_calls or [])
        ]
        total = r.usage.total_tokens if getattr(r, "usage", None) else 0
        return RespostaLLM(content=msg.content, tool_calls=chamadas, tokens=total)


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
