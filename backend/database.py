import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

URL_DATABASE = os.getenv("DATABASE_URL")
if not URL_DATABASE:
    raise RuntimeError(
        "A variável de ambiente DATABASE_URL não está configurada."
    )

engine = create_engine(URL_DATABASE)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
