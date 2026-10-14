from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


CategoriaTransacao = Literal[
    "Alimentação",
    "Moradia",
    "Transporte",
    "Lazer",
    "Salário",
    "Contas Gerais",
    "Contas Fixas",
]
MetodoPagamento = Literal["Dinheiro", "Débito", "Cartão de Crédito"]


class UsuarioCriacao(BaseModel):
    nome: str = Field(min_length=1, max_length=100)
    email: EmailStr
    senha: str = Field(min_length=8, max_length=72)

    @field_validator("nome")
    @classmethod
    def validar_nome(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("O nome não pode estar vazio.")
        return valor

    @field_validator("senha")
    @classmethod
    def validar_tamanho_senha(cls, valor: str) -> str:
        if len(valor.encode("utf-8")) > 72:
            raise ValueError("A senha não pode exceder 72 bytes em UTF-8.")
        return valor


class UsuarioResposta(BaseModel):
    id: int
    nome: str
    email: str
    tipo: str

    model_config = ConfigDict(from_attributes=True)


class TransacaoCriacao(BaseModel):
    descricao: str = Field(min_length=1, max_length=255)
    valor: float = Field(gt=0, allow_inf_nan=False)
    tipo: Literal["receita", "despesa"]
    categoria: CategoriaTransacao = "Contas Gerais"
    categoria_detalhe: str | None = Field(default=None, max_length=100)
    metodo_pagamento: MetodoPagamento = "Dinheiro"

    @field_validator("descricao")
    @classmethod
    def validar_descricao(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("A descrição não pode estar vazia.")
        return valor


class TransacaoResposta(BaseModel):
    id: int
    descricao: str
    valor: float
    tipo: str
    categoria: CategoriaTransacao
    categoria_detalhe: str | None
    metodo_pagamento: MetodoPagamento
    data: datetime
    usuario_id: int
    usuario_nome: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ResumoDespesasMembro(BaseModel):
    usuario_id: int
    usuario_nome: str
    total_despesas: float
