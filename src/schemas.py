from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class EntradaAtendimento(BaseModel):
    """Texto digitado + identificadores que acompanham o texto."""

    mensagem: str
    contrato: str = Field(description="Vem da sessão, não é digitado pelo cliente.")
    thread_id: str = Field(description="Gerado pelo sistema: contrato + id do atendimento.")


class Fonte(BaseModel):
    tipo: Literal["ferramenta", "corpus"]
    id: str = Field(description="Nome da ferramenta ou id do trecho do corpus.")
    detalhe: Optional[str] = None


class RespostaAtendimento(BaseModel):
    resultado: str = Field(min_length=1)
    fontes: List[Fonte] = Field(default_factory=list)
    suficiente: bool
    motivo_insuficiencia: Optional[str] = None
    encaminhar_humano: bool = False
    motivo_parada: str
    citacoes_invalidas: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _coerencia(self):
        if self.suficiente and not self.fontes:
            raise ValueError(
                "suficiente=True exige ao menos uma fonte conferível (ferramenta ou corpus)"
            )
        if not self.suficiente and not self.motivo_insuficiencia:
            raise ValueError("suficiente=False exige motivo_insuficiencia")
        return self
