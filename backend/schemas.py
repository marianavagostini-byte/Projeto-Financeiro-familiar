from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Literal


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
    nome: str
    email: EmailStr
    senha: str


class UsuarioResposta(BaseModel):
    id: int
    nome: str
    email: str
    tipo: str

    class Config:
        from_attributes = True


class TransacaoCriacao(BaseModel):
    descricao: str = Field(max_length=255)
    valor: float = Field(gt=0)
    tipo: str  # "receita" ou "despesa"
    categoria: CategoriaTransacao = "Contas Gerais"
    categoria_detalhe: str | None = Field(default=None, max_length=100)
    metodo_pagamento: MetodoPagamento = "Dinheiro"


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

    class Config:
        from_attributes = True


class ResumoDespesasMembro(BaseModel):
    usuario_id: int
    usuario_nome: str
    total_despesas: float
