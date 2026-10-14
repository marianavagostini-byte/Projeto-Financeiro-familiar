import os
from contextlib import asynccontextmanager
from datetime import date, datetime, time, timedelta, timezone
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import and_, func, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from backend.database import SessionLocal, engine
import backend.models as models
import backend.schemas as schemas
from backend.schemas import TransacaoCriacao, TransacaoResposta
from backend.models import Usuario, Transacao

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY or len(SECRET_KEY) < 32 or SECRET_KEY.startswith("replace_"):
    raise RuntimeError(
        "Configure SECRET_KEY com uma chave aleatória de pelo menos 32 caracteres."
    )

def migrar_colunas_de_transacao():
    with engine.begin() as conexao:
        colunas_existentes = {
            coluna["name"]
            for coluna in inspect(conexao).get_columns("transacoes")
        }
        if "categoria" not in colunas_existentes:
            conexao.execute(
                text(
                    "ALTER TABLE transacoes ADD COLUMN categoria "
                    "VARCHAR(100) NOT NULL DEFAULT 'Contas Gerais'"
                )
            )
        if "categoria_detalhe" not in colunas_existentes:
            conexao.execute(
                text("ALTER TABLE transacoes ADD COLUMN categoria_detalhe VARCHAR(100)")
            )
        if "metodo_pagamento" not in colunas_existentes:
            conexao.execute(
                text(
                    "ALTER TABLE transacoes ADD COLUMN metodo_pagamento "
                    "VARCHAR(50) NOT NULL DEFAULT 'Dinheiro'"
                )
            )


@asynccontextmanager
async def lifespan(_: FastAPI):
    models.Base.metadata.create_all(bind=engine)
    migrar_colunas_de_transacao()
    yield


app = FastAPI(lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def tratar_erro_validacao(
    _: Request, excecao: RequestValidationError
) -> JSONResponse:
    erros = [
        {
            "loc": erro["loc"],
            "msg": erro["msg"],
            "type": erro["type"],
        }
        for erro in excecao.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": erros})


origens_frontend = [
    origem.strip()
    for origem in os.getenv(
        "FRONTEND_ORIGINS",
        "http://127.0.0.1:5500,http://localhost:5500",
    ).split(",")
    if origem.strip()
]

# Configuração de CORS para permitir que o frontend aceda à API
app.add_middleware(
    CORSMiddleware,
    allow_origins=origens_frontend,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurações de Segurança e JWT
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
CATEGORIAS_RESTRITAS = {"Moradia", "Contas Fixas"}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def criar_token_acesso(data: dict):
    dados_a_codificar = data.copy()
    expiracao = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    dados_a_codificar.update({"exp": expiracao})
    return jwt.encode(dados_a_codificar, SECRET_KEY, algorithm=ALGORITHM)


def obter_utilizador_atual(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if usuario is None:
        raise credentials_exception
    return usuario


@app.post("/usuarios/", status_code=status.HTTP_201_CREATED)
def criar_usuario(usuario: schemas.UsuarioCriacao, db: Session = Depends(get_db)):
    db_user = db.query(Usuario).filter(Usuario.email == usuario.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este e-mail já está registado.",
        )

    senha_hash = pwd_context.hash(usuario.senha)
    db_usuario = Usuario(
        nome=usuario.nome, email=usuario.email, senha_hash=senha_hash, tipo="membro"
    )
    db.add(db_usuario)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este e-mail já está registado.",
        )
    db.refresh(db_usuario)
    return {"mensagem": "Utilizador criado com sucesso!", "nome": db_usuario.nome}


@app.post("/token")
def login_para_obter_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    usuario = db.query(Usuario).filter(Usuario.email == form_data.username).first()

    if not usuario or not pwd_context.verify(form_data.password, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = criar_token_acesso(data={"sub": usuario.email, "tipo": usuario.tipo})
    return {"access_token": access_token, "token_type": "bearer", "tipo": usuario.tipo}


@app.post(
    "/transacoes/",
    response_model=TransacaoResposta,
    status_code=status.HTTP_201_CREATED,
)
def criar_transacao(
    transacao: TransacaoCriacao,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_utilizador_atual),
):
    if (
        transacao.categoria in CATEGORIAS_RESTRITAS
        and usuario_atual.tipo != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem registar transações nesta categoria.",
        )

    nova_transacao = Transacao(
        descricao=transacao.descricao,
        valor=transacao.valor,
        tipo=transacao.tipo,
        categoria=transacao.categoria,
        categoria_detalhe=transacao.categoria_detalhe,
        metodo_pagamento=transacao.metodo_pagamento,
        usuario_id=usuario_atual.id,
    )
    db.add(nova_transacao)
    db.commit()
    db.refresh(nova_transacao)
    return nova_transacao


@app.get(
    "/transacoes/resumo-membros",
    response_model=list[schemas.ResumoDespesasMembro],
)
def resumo_despesas_membros(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_utilizador_atual),
    inicio: date | None = None,
    fim: date | None = None,
):
    if usuario_atual.tipo != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem consultar o resumo familiar.",
        )
    if inicio and fim and inicio > fim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A data inicial não pode ser posterior à data final.",
        )

    condicoes_join = [
        Transacao.usuario_id == Usuario.id,
        Transacao.tipo == "despesa",
    ]
    if inicio:
        condicoes_join.append(
            Transacao.data >= datetime.combine(inicio, time.min)
        )
    if fim:
        condicoes_join.append(
            Transacao.data < datetime.combine(fim + timedelta(days=1), time.min)
        )

    resultados = (
        db.query(
            Usuario.id.label("usuario_id"),
            Usuario.nome.label("usuario_nome"),
            func.coalesce(
                func.sum(func.abs(Transacao.valor)), 0
            ).label("total_despesas"),
        )
        .outerjoin(Transacao, and_(*condicoes_join))
        .group_by(Usuario.id, Usuario.nome)
        .order_by(Usuario.nome, Usuario.id)
        .all()
    )
    return [
        {
            "usuario_id": resultado.usuario_id,
            "usuario_nome": resultado.usuario_nome,
            "total_despesas": resultado.total_despesas,
        }
        for resultado in resultados
    ]


@app.get("/transacoes/", response_model=list[TransacaoResposta])
def listar_transacoes(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_utilizador_atual),
    inicio: date | None = None,
    fim: date | None = None,
    member_id: int | None = None,
):
    if inicio and fim and inicio > fim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A data inicial não pode ser posterior à data final.",
        )

    consulta = db.query(Transacao)
    if usuario_atual.tipo != "admin":
        if member_id is not None and member_id != usuario_atual.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Só pode consultar as próprias transações.",
            )
        consulta = consulta.filter(
            Transacao.usuario_id == usuario_atual.id,
            ~Transacao.categoria.in_(CATEGORIAS_RESTRITAS),
        )
    elif member_id is not None:
        consulta = consulta.filter(Transacao.usuario_id == member_id)

    if inicio:
        consulta = consulta.filter(
            Transacao.data >= datetime.combine(inicio, time.min)
        )
    if fim:
        consulta = consulta.filter(
            Transacao.data < datetime.combine(fim + timedelta(days=1), time.min)
        )

    return (
        consulta.options(joinedload(Transacao.usuario))
        .order_by(Transacao.data.desc())
        .all()
    )
