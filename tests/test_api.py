import json
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt
from sqlalchemy import inspect, text

from backend.database import Base, engine
from backend.main import ALGORITHM, SECRET_KEY, pwd_context
from backend.main import migrar_colunas_de_transacao
from backend.models import Transacao, Usuario


def cadastrar(client, email="membro@example.com", **campos):
    dados = {
        "nome": "Membro de Teste",
        "email": email,
        "senha": "senha-segura-123",
        **campos,
    }
    return client.post("/usuarios/", json=dados)


def obter_token(client, email="membro@example.com", senha="senha-segura-123"):
    resposta = client.post(
        "/token",
        data={"username": email, "password": senha},
    )
    assert resposta.status_code == 200
    return resposta.json()["access_token"]


def autenticacao(token):
    return {"Authorization": f"Bearer {token}"}


def criar_transacao(client, token, **campos):
    dados = {
        "descricao": "Despesa de teste",
        "valor": 25.5,
        "tipo": "despesa",
        "categoria": "Alimentação",
        "metodo_pagamento": "Dinheiro",
        **campos,
    }
    return client.post("/transacoes/", json=dados, headers=autenticacao(token))


@pytest.fixture
def membro(client):
    resposta = cadastrar(client)
    assert resposta.status_code == 201
    return {
        "email": "membro@example.com",
        "token": obter_token(client),
    }


@pytest.fixture
def administrador(client, test_db):
    with test_db() as db:
        db.add(
            Usuario(
                nome="Administradora de Teste",
                email="admin@example.com",
                senha_hash=pwd_context.hash("senha-admin-segura-123"),
                tipo="admin",
            )
        )
        db.commit()
    return {
        "email": "admin@example.com",
        "token": obter_token(client, "admin@example.com", "senha-admin-segura-123"),
    }


def test_app_inicia_e_documenta_api(client):
    assert client.get("/docs").status_code == 200
    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    assert {
        "/usuarios/",
        "/token",
        "/transacoes/",
        "/transacoes/resumo-membros",
    }.issubset(openapi.json()["paths"])
    assert set(openapi.json()["paths"]["/transacoes/"]) == {"get", "post"}


def test_nao_existem_rotas_de_edicao_ou_exclusao_de_transacoes(client, membro):
    criada = criar_transacao(client, membro["token"])
    transacao_id = criada.json()["id"]

    edicao = client.put(
        f"/transacoes/{transacao_id}",
        json={"descricao": "Tentativa de edição"},
        headers=autenticacao(membro["token"]),
    )
    exclusao = client.delete(
        f"/transacoes/{transacao_id}",
        headers=autenticacao(membro["token"]),
    )
    listagem = client.get(
        "/transacoes/",
        headers=autenticacao(membro["token"]),
    )

    assert criada.status_code == 201
    assert edicao.status_code == 404
    assert exclusao.status_code == 404
    assert [item["id"] for item in listagem.json()] == [transacao_id]


def test_cadastro_valido_nao_permite_definir_perfil(client):
    resposta = cadastrar(client, tipo="admin")

    assert resposta.status_code == 201
    token = obter_token(client)
    resposta_login = client.post(
        "/token",
        data={"username": "membro@example.com", "password": "senha-segura-123"},
    )
    assert resposta_login.status_code == 200
    assert resposta_login.json()["tipo"] == "membro"
    assert token


@pytest.mark.parametrize(
    "email,dados",
    [
        ("não-é-email", {}),
        ("outro@example.com", {"nome": "   "}),
        ("outro@example.com", {"senha": "curta"}),
        ("outro@example.com", {"senha": "á" * 37}),
    ],
)
def test_cadastro_rejeita_dados_invalidos(client, email, dados):
    resposta = cadastrar(client, email=email, **dados)
    assert resposta.status_code == 422


def test_cadastro_rejeita_email_duplicado(client):
    assert cadastrar(client).status_code == 201
    resposta = cadastrar(client)
    assert resposta.status_code == 409


def test_login_valido_e_invalido(client, membro):
    resposta_valida = client.post(
        "/token",
        data={"username": membro["email"], "password": "senha-segura-123"},
    )
    resposta_invalida = client.post(
        "/token",
        data={"username": membro["email"], "password": "senha-incorreta"},
    )

    assert resposta_valida.status_code == 200
    assert resposta_valida.json()["token_type"] == "bearer"
    assert resposta_invalida.status_code == 401
    assert resposta_invalida.headers["www-authenticate"] == "Bearer"


def test_rotas_protegidas_rejeitam_token_ausente_invalido_e_expirado(client):
    agora = datetime.now(timezone.utc)
    token_expirado = jwt.encode(
        {
            "sub": "membro@example.com",
            "exp": agora - timedelta(minutes=1),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    for cabecalhos in (
        {},
        autenticacao("token-invalido"),
        autenticacao(token_expirado),
    ):
        resposta = client.get("/transacoes/", headers=cabecalhos)
        assert resposta.status_code == 401


def test_membro_cria_e_lista_apenas_as_proprias_transacoes(client, membro):
    outro = cadastrar(client, email="outro@example.com")
    assert outro.status_code == 201
    token_outro = obter_token(client, "outro@example.com")

    criada = criar_transacao(client, membro["token"])
    resposta_propria = client.get(
        "/transacoes/",
        headers=autenticacao(membro["token"]),
    )
    resposta_alheia = client.get(
        "/transacoes/",
        headers=autenticacao(token_outro),
    )

    assert criada.status_code == 201
    assert len(resposta_propria.json()) == 1
    assert resposta_propria.json()[0]["id"] == criada.json()["id"]
    assert resposta_alheia.json() == []


def test_membro_nao_pode_acessar_transacoes_de_outro_membro(client, membro):
    assert cadastrar(client, email="outro@example.com").status_code == 201
    outra = obter_token(client, "outro@example.com")
    resposta = client.get(
        "/transacoes/?member_id=2",
        headers=autenticacao(membro["token"]),
    )
    resposta_resumo = client.get(
        "/transacoes/resumo-membros",
        headers=autenticacao(membro["token"]),
    )

    assert resposta.status_code == 403
    assert resposta_resumo.status_code == 403
    assert outra


@pytest.mark.parametrize(
    "campos",
    [
        {"tipo": "transferência"},
        {"valor": 0},
        {"valor": float("nan")},
        {"categoria": "Categoria desconhecida"},
    ],
)
def test_criacao_de_transacao_rejeita_campos_invalidos(client, membro, campos):
    dados = {
        "descricao": "Despesa de teste",
        "valor": 25.5,
        "tipo": "despesa",
        "categoria": "Alimentação",
        "metodo_pagamento": "Dinheiro",
        **campos,
    }
    if isinstance(dados["valor"], float) and dados["valor"] != dados["valor"]:
        resposta = client.post(
            "/transacoes/",
            content=json.dumps(dados, allow_nan=True),
            headers={
                **autenticacao(membro["token"]),
                "Content-Type": "application/json",
            },
        )
    else:
        resposta = client.post(
            "/transacoes/",
            json=dados,
            headers=autenticacao(membro["token"]),
        )
    assert resposta.status_code == 422
    assert "input" not in resposta.json()["detail"][0]


def test_categoria_restrita_e_visibilidade_exigem_admin(
    client, membro, administrador
):
    resposta_membro = criar_transacao(
        client,
        membro["token"],
        categoria="Moradia",
    )
    resposta_admin = criar_transacao(
        client,
        administrador["token"],
        categoria="Moradia",
    )
    lista_membro = client.get(
        "/transacoes/",
        headers=autenticacao(membro["token"]),
    )
    lista_admin = client.get(
        "/transacoes/",
        headers=autenticacao(administrador["token"]),
    )

    assert resposta_membro.status_code == 403
    assert resposta_admin.status_code == 201
    assert lista_membro.json() == []
    assert len(lista_admin.json()) == 1


def test_admin_pode_filtrar_transacoes_por_membro(
    client, membro, administrador
):
    criada = criar_transacao(client, membro["token"])
    resposta = client.get(
        f"/transacoes/?member_id={criada.json()['usuario_id']}",
        headers=autenticacao(administrador["token"]),
    )

    assert resposta.status_code == 200
    assert [item["id"] for item in resposta.json()] == [criada.json()["id"]]


def test_listagem_filtra_transacoes_pelo_intervalo_de_datas(
    client, membro, test_db
):
    with test_db() as db:
        usuario = db.query(Usuario).filter_by(email=membro["email"]).one()
        db.add_all(
            [
                Transacao(
                    descricao="Dentro do período",
                    valor=12.5,
                    tipo="despesa",
                    categoria="Alimentação",
                    metodo_pagamento="Dinheiro",
                    data=datetime(2024, 2, 12, 12),
                    usuario_id=usuario.id,
                ),
                Transacao(
                    descricao="Fora do período",
                    valor=9.5,
                    tipo="despesa",
                    categoria="Alimentação",
                    metodo_pagamento="Dinheiro",
                    data=datetime(2024, 2, 9, 12),
                    usuario_id=usuario.id,
                ),
            ]
        )
        db.commit()

    resposta = client.get(
        "/transacoes/?inicio=2024-02-10&fim=2024-02-12",
        headers=autenticacao(membro["token"]),
    )

    assert resposta.status_code == 200
    assert [item["descricao"] for item in resposta.json()] == ["Dentro do período"]


def test_resumo_admin_respeita_intervalo_de_datas(client, administrador, test_db):
    with test_db() as db:
        membro_db = Usuario(
            nome="Membro do Resumo",
            email="resumo@example.com",
            senha_hash=pwd_context.hash("senha-resumo-segura-123"),
            tipo="membro",
        )
        db.add(membro_db)
        db.flush()
        db.add_all(
            [
                Transacao(
                    descricao="Despesa dentro do período",
                    valor=20,
                    tipo="despesa",
                    categoria="Alimentação",
                    metodo_pagamento="Dinheiro",
                    data=datetime(2024, 2, 12, 12),
                    usuario_id=membro_db.id,
                ),
                Transacao(
                    descricao="Despesa fora do período",
                    valor=40,
                    tipo="despesa",
                    categoria="Alimentação",
                    metodo_pagamento="Dinheiro",
                    data=datetime(2024, 2, 9, 12),
                    usuario_id=membro_db.id,
                ),
                Transacao(
                    descricao="Receita dentro do período",
                    valor=100,
                    tipo="receita",
                    categoria="Salário",
                    metodo_pagamento="Dinheiro",
                    data=datetime(2024, 2, 12, 12),
                    usuario_id=membro_db.id,
                ),
            ]
        )
        db.commit()

    resposta = client.get(
        "/transacoes/resumo-membros?inicio=2024-02-10&fim=2024-02-12",
        headers=autenticacao(administrador["token"]),
    )
    totais = {item["usuario_nome"]: item["total_despesas"] for item in resposta.json()}

    assert resposta.status_code == 200
    assert totais["Membro do Resumo"] == 20
    assert totais["Administradora de Teste"] == 0


def test_resumo_de_despesas_agrega_centavos_sem_regra_de_arredondamento(
    client, administrador, test_db
):
    with test_db() as db:
        membro_db = Usuario(
            nome="Membro de Centavos",
            email="centavos@example.com",
            senha_hash=pwd_context.hash("senha-centavos-segura-123"),
            tipo="membro",
        )
        db.add(membro_db)
        db.flush()
        db.add_all(
            [
                Transacao(
                    descricao="Primeira parcela",
                    valor=0.1,
                    tipo="despesa",
                    categoria="Alimentação",
                    metodo_pagamento="Dinheiro",
                    usuario_id=membro_db.id,
                ),
                Transacao(
                    descricao="Segunda parcela",
                    valor=0.2,
                    tipo="despesa",
                    categoria="Alimentação",
                    metodo_pagamento="Dinheiro",
                    usuario_id=membro_db.id,
                ),
            ]
        )
        db.commit()

    resposta = client.get(
        "/transacoes/resumo-membros",
        headers=autenticacao(administrador["token"]),
    )
    totais = {item["usuario_nome"]: item["total_despesas"] for item in resposta.json()}

    assert resposta.status_code == 200
    assert totais["Membro de Centavos"] == pytest.approx(0.3)


def test_valores_fracionarios_passam_pela_api_e_sao_agregados(
    client, administrador
):
    primeira = criar_transacao(
        client,
        administrador["token"],
        descricao="Primeira despesa fracionária",
        valor=0.1,
    )
    segunda = criar_transacao(
        client,
        administrador["token"],
        descricao="Segunda despesa fracionária",
        valor=0.2,
    )

    assert primeira.status_code == 201
    assert primeira.json()["valor"] == pytest.approx(0.1)
    assert segunda.status_code == 201
    assert segunda.json()["valor"] == pytest.approx(0.2)

    listagem = client.get(
        "/transacoes/",
        headers=autenticacao(administrador["token"]),
    )
    resumo = client.get(
        "/transacoes/resumo-membros",
        headers=autenticacao(administrador["token"]),
    )

    assert listagem.status_code == 200
    valores_por_descricao = {
        item["descricao"]: item["valor"] for item in listagem.json()
    }
    assert valores_por_descricao == pytest.approx(
        {
            "Primeira despesa fracionária": 0.1,
            "Segunda despesa fracionária": 0.2,
        }
    )
    totais = {item["usuario_nome"]: item["total_despesas"] for item in resumo.json()}
    assert resumo.status_code == 200
    assert totais["Administradora de Teste"] == pytest.approx(0.3)


def test_filtros_rejeitam_intervalo_invertido(client, membro):
    resposta = client.get(
        "/transacoes/?inicio=2024-02-12&fim=2024-02-10",
        headers=autenticacao(membro["token"]),
    )
    assert resposta.status_code == 400


def test_cors_permite_origens_locais_e_rejeita_origem_desconhecida(client):
    cabecalhos_preflight = {
        "Access-Control-Request-Method": "GET",
        "Origin": "http://127.0.0.1:5500",
    }
    permitida = client.options("/transacoes/", headers=cabecalhos_preflight)
    bloqueada = client.options(
        "/transacoes/",
        headers={
            **cabecalhos_preflight,
            "Origin": "https://site-nao-configurado.example",
        },
    )

    assert permitida.headers["access-control-allow-origin"] == "http://127.0.0.1:5500"
    assert "access-control-allow-origin" not in bloqueada.headers


def test_migracao_adiciona_colunas_sem_apagar_registros_existentes(client):
    Base.metadata.drop_all(bind=engine)
    with engine.begin() as conexao:
        conexao.exec_driver_sql(
            "CREATE TABLE transacoes ("
            "id INTEGER PRIMARY KEY, descricao VARCHAR(255) NOT NULL, "
            "valor FLOAT NOT NULL, tipo VARCHAR(50) NOT NULL, "
            "data DATETIME, usuario_id INTEGER)"
        )
        conexao.execute(
            text(
                "INSERT INTO transacoes "
                "(id, descricao, valor, tipo, data, usuario_id) "
                "VALUES (1, 'Registo preservado', 12.5, 'despesa', "
                "'2024-01-01 00:00:00', 1)"
            )
        )

    migrar_colunas_de_transacao()

    with engine.connect() as conexao:
        colunas = {
            coluna["name"]
            for coluna in inspect(conexao).get_columns("transacoes")
        }
        registo = conexao.execute(
            text("SELECT descricao, valor FROM transacoes WHERE id = 1")
        ).one()

    assert {"categoria", "categoria_detalhe", "metodo_pagamento"} <= colunas
    assert registo.descricao == "Registo preservado"
    assert registo.valor == 12.5

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
