from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, text
from sqlalchemy.orm import relationship
import datetime

from backend.database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)
    tipo = Column(String(50), default="membro")  # "admin" ou "membro"

    transacoes = relationship("Transacao", back_populates="usuario")


class Transacao(Base):
    __tablename__ = "transacoes"

    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(String(255), nullable=False)
    valor = Column(Float, nullable=False)
    tipo = Column(String(50), nullable=False)  # "receita" ou "despesa"
    categoria = Column(
        String(100),
        nullable=False,
        default="Contas Gerais",
        server_default=text("'Contas Gerais'"),
    )
    categoria_detalhe = Column(String(100), nullable=True)
    metodo_pagamento = Column(
        String(50),
        nullable=False,
        default="Dinheiro",
        server_default=text("'Dinheiro'"),
    )
    data = Column(DateTime, default=datetime.datetime.utcnow)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))

    usuario = relationship("Usuario", back_populates="transacoes")

    @property
    def usuario_nome(self):
        return self.usuario.nome if self.usuario else None
