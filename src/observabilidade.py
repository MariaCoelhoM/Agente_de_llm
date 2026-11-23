"""
Instrumentação OpenTelemetry nas convenções semânticas GenAI (Parte 3, §4.2).

Três spans, como pede o enunciado:
  invoke_agent suporte_tecnico_domestico   raiz, um por turno da conversa
  chat <modelo>                            cada chamada ao modelo
  execute_tool <ferramenta>                cada ferramenta executada

A raiz carrega os atributos próprios do case (prefixo `app.`), entre eles os
dois obrigatórios: `app.motivo_termino` e `app.versao_sistema`. O trace é o
registro da decisão (§2.3): entrada, trechos recuperados, versões, ferramentas
com argumentos e resultado, saída, motivo de término e aprovação humana.

Destino: arquivo JSONL (um span por linha) em logs/traces/AAAA-MM-DD.jsonl, ou
no caminho que a suíte de avaliação definir com `redirecionar()`. Se a variável
OTEL_EXPORTER_OTLP_ENDPOINT existir, os spans também vão por OTLP/HTTP para um
coletor (Jaeger, Phoenix, Grafana Tempo...). Ver README, "Como ver os traces".

Os nós do LangGraph podem rodar em outra thread, então o span pai é passado
explicitamente (pelo thread_id da conversa), e não pelo contexto implícito.
"""
import datetime
import hashlib
import json
import os
import threading
from contextlib import contextmanager
from typing import Dict, Optional

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.trace import Status, StatusCode

from . import config

NOME_AGENTE = "suporte_tecnico_domestico"
LIMITE_TEXTO = 600  # caracteres de argumento/resultado guardados por atributo


def _iso(ns: int) -> str:
    return datetime.datetime.fromtimestamp(ns / 1e9, tz=datetime.timezone.utc).isoformat(timespec="milliseconds")


class ExportadorArquivo(SpanExporter):
    """Grava cada span como uma linha JSON. Destino padrão: um arquivo por dia."""

    def __init__(self):
        self.destino: Optional[str] = None
        self._trava = threading.Lock()

    def _caminho(self) -> str:
        if self.destino:
            return self.destino
        return os.path.join(config.PASTA_TRACES, f"{datetime.date.today().isoformat()}.jsonl")

    def export(self, spans):
        caminho = self._caminho()
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with self._trava, open(caminho, "a", encoding="utf-8") as arquivo:
            for s in spans:
                ctx = s.get_span_context()
                registro = {
                    "trace_id": format(ctx.trace_id, "032x"),
                    "span_id": format(ctx.span_id, "016x"),
                    "parent_id": format(s.parent.span_id, "016x") if s.parent else None,
                    "nome": s.name,
                    "inicio": _iso(s.start_time),
                    "fim": _iso(s.end_time),
                    "duracao_ms": round((s.end_time - s.start_time) / 1e6, 2),
                    "status": s.status.status_code.name,
                    "atributos": dict(s.attributes or {}),
                    "eventos": [{"nome": e.name, "quando": _iso(e.timestamp), "atributos": dict(e.attributes or {})}
                                for e in s.events],
                }
                arquivo.write(json.dumps(registro, ensure_ascii=False) + "\n")
        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass


_exportador = ExportadorArquivo()
_provedor: Optional[TracerProvider] = None
_raizes: Dict[str, trace.Span] = {}


def _configurar() -> TracerProvider:
    global _provedor
    if _provedor is None:
        recurso = Resource.create({"service.name": NOME_AGENTE, "service.version": config.VERSAO_SISTEMA})
        _provedor = TracerProvider(resource=recurso)
        _provedor.add_span_processor(SimpleSpanProcessor(_exportador))
        if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            _provedor.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    return _provedor


def tracer():
    return _configurar().get_tracer("agente_suporte", config.VERSAO_SISTEMA)


def redirecionar(caminho: Optional[str]):
    """A suíte de avaliação grava os traces de cada rodada dentro da pasta da rodada."""
    _configurar()
    _exportador.destino = caminho


def descarregar():
    if _provedor is not None:
        _provedor.force_flush()


def provedor_do_modelo() -> str:
    url = os.environ.get("LLM_BASE_URL", "")
    for chave, nome in (("groq", "groq"), ("mistral", "mistral_ai"), ("openai", "openai"), ("localhost", "local")):
        if chave in url:
            return nome
    return "desconhecido"


def texto_curto(valor) -> str:
    texto = valor if isinstance(valor, str) else json.dumps(valor, ensure_ascii=False, default=str)
    return texto[:LIMITE_TEXTO]


def sha12(texto: str) -> str:
    return hashlib.sha256((texto or "").encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------- raiz por turno

@contextmanager
def span_turno(thread_id: str, modelo: str, atributos: dict):
    """Abre a raiz `invoke_agent` do turno e a registra para os nós usarem como pai."""
    t = tracer()
    with t.start_as_current_span(f"invoke_agent {NOME_AGENTE}", kind=trace.SpanKind.INTERNAL) as raiz:
        raiz.set_attribute("gen_ai.operation.name", "invoke_agent")
        raiz.set_attribute("gen_ai.agent.name", NOME_AGENTE)
        raiz.set_attribute("gen_ai.provider.name", provedor_do_modelo())
        raiz.set_attribute("gen_ai.request.model", modelo)
        raiz.set_attribute("gen_ai.conversation.id", thread_id)
        raiz.set_attribute("app.versao_sistema", config.VERSAO_SISTEMA)
        for chave, valor in atributos.items():
            if valor is not None:
                raiz.set_attribute(chave, valor)
        _raizes[thread_id] = raiz
        try:
            yield raiz
        finally:
            _raizes.pop(thread_id, None)


def raiz(thread_id: str) -> Optional[trace.Span]:
    return _raizes.get(thread_id)


@contextmanager
def span_filho(thread_id: str, nome: str):
    pai = _raizes.get(thread_id)
    contexto = trace.set_span_in_context(pai) if pai is not None else None
    with tracer().start_as_current_span(nome, context=contexto) as span:
        yield span


def marcar_erro(span, descricao: str):
    span.set_status(Status(StatusCode.ERROR, descricao))


def evento_raiz(thread_id: str, nome: str, atributos: dict):
    r = _raizes.get(thread_id)
    if r is not None:
        r.add_event(nome, {k: v for k, v in atributos.items() if v is not None})


def custo_usd(tokens_entrada: int, tokens_saida: int) -> float:
    return round(tokens_entrada / 1e6 * config.PRECO_ENTRADA_MTOK
                 + tokens_saida / 1e6 * config.PRECO_SAIDA_MTOK, 6)
