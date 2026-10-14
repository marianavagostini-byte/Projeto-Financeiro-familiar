"""Teste manual de integração contra uma API e contas de desenvolvimento existentes."""

import os
from uuid import uuid4

import requests


BASE_URL = os.getenv("TEST_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
EMAIL_MEMBRO = os.getenv("TEST_MEMBER_EMAIL")
SENHA_MEMBRO = os.getenv("TEST_MEMBER_PASSWORD")
EMAIL_ADMIN = os.getenv("TEST_ADMIN_EMAIL")
SENHA_ADMIN = os.getenv("TEST_ADMIN_PASSWORD")
TIMEOUT_SEGUNDOS = 10


def autenticar(email: str, senha: str, perfil: str) -> str:
    resposta = requests.post(
        f"{BASE_URL}/token",
        data={"username": email, "password": senha},
        timeout=TIMEOUT_SEGUNDOS,
    )
    if resposta.status_code != 200:
        raise RuntimeError(
            f"Falha ao autenticar a conta de {perfil}: HTTP {resposta.status_code}."
        )

    token = resposta.json().get("access_token")
    if not token:
        raise RuntimeError(f"A API não devolveu um token para a conta de {perfil}.")
    return token


def executar() -> None:
    variaveis_em_falta = [
        nome
        for nome, valor in (
            ("TEST_MEMBER_EMAIL", EMAIL_MEMBRO),
            ("TEST_MEMBER_PASSWORD", SENHA_MEMBRO),
            ("TEST_ADMIN_EMAIL", EMAIL_ADMIN),
            ("TEST_ADMIN_PASSWORD", SENHA_ADMIN),
        )
        if not valor
    ]
    if variaveis_em_falta:
        raise RuntimeError(
            "Configure as variáveis de ambiente de teste: "
            + ", ".join(variaveis_em_falta)
        )

    token_membro = autenticar(EMAIL_MEMBRO, SENHA_MEMBRO, "membro")
    token_admin = autenticar(EMAIL_ADMIN, SENHA_ADMIN, "admin")
    cabecalhos_membro = {"Authorization": f"Bearer {token_membro}"}
    cabecalhos_admin = {"Authorization": f"Bearer {token_admin}"}
    descricao = f"Teste de integração {uuid4().hex[:12]}"

    resposta_criacao = requests.post(
        f"{BASE_URL}/transacoes/",
        json={
            "descricao": descricao,
            "valor": 50.0,
            "tipo": "despesa",
            "categoria": "Alimentação",
            "metodo_pagamento": "Dinheiro",
        },
        headers=cabecalhos_membro,
        timeout=TIMEOUT_SEGUNDOS,
    )
    if resposta_criacao.status_code != 201:
        raise RuntimeError(
            "Falha ao criar a transação de teste: "
            f"HTTP {resposta_criacao.status_code}."
        )

    id_transacao = resposta_criacao.json().get("id")
    if id_transacao is None:
        raise RuntimeError("A API não devolveu o identificador da transação criada.")

    resposta_membro = requests.get(
        f"{BASE_URL}/transacoes/",
        headers=cabecalhos_membro,
        timeout=TIMEOUT_SEGUNDOS,
    )
    if resposta_membro.status_code != 200:
        raise RuntimeError(
            f"Falha ao listar transações como membro: HTTP {resposta_membro.status_code}."
        )
    if not any(item.get("id") == id_transacao for item in resposta_membro.json()):
        raise RuntimeError("O membro não encontrou a transação que acabou de criar.")

    resposta_admin = requests.get(
        f"{BASE_URL}/transacoes/",
        headers=cabecalhos_admin,
        timeout=TIMEOUT_SEGUNDOS,
    )
    if resposta_admin.status_code != 200:
        raise RuntimeError(
            f"Falha ao listar transações como admin: HTTP {resposta_admin.status_code}."
        )
    if not any(item.get("id") == id_transacao for item in resposta_admin.json()):
        raise RuntimeError("O administrador não encontrou a transação de teste.")

    print("Teste de integração concluído: autenticação, criação e leitura autorizada.")
    print(
        "Foi criada uma transação fictícia na base de dados configurada. "
        "Remova-a manualmente se necessário."
    )


if __name__ == "__main__":
    executar()
