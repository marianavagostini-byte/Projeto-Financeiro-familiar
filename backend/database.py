import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

URL_DATABASE = os.getenv("DATABASE_URL")
if not URL_DATABASE:
    raise RuntimeError(
        "A variável de ambiente DATABASE_URL não está configurada."
    )

opcoes_engine = {}
if URL_DATABASE.startswith("sqlite"):
    opcoes_engine["connect_args"] = {"check_same_thread": False}
    if URL_DATABASE in {"sqlite://", "sqlite:///:memory:"}:
        opcoes_engine["poolclass"] = StaticPool

engine = create_engine(URL_DATABASE, **opcoes_engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
