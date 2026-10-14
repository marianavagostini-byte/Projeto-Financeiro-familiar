import os

import requests

BASE_URL = os.getenv("TEST_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
EMAIL_MEMBRO = os.getenv("TEST_MEMBER_EMAIL")
SENHA_MEMBRO = os.getenv("TEST_MEMBER_PASSWORD")
EMAIL_ADMIN = os.getenv("TEST_ADMIN_EMAIL")
SENHA_ADMIN = os.getenv("TEST_ADMIN_PASSWORD")

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

print("--- A INICIAR TESTES DE RBAC E TRANSAÇÕES ---")

# 1. Login Membro
res_login_membro = requests.post(
    f"{BASE_URL}/token",
    data={"username": EMAIL_MEMBRO, "password": SENHA_MEMBRO},
    timeout=10,
)
res_login_membro.raise_for_status()
token_membro = res_login_membro.json().get("access_token")

# 2. Login Admin
res_login_admin = requests.post(
    f"{BASE_URL}/token",
    data={"username": EMAIL_ADMIN, "password": SENHA_ADMIN},
    timeout=10,
)
res_login_admin.raise_for_status()
token_admin = res_login_admin.json().get("access_token")

if token_membro and token_admin:
    headers_membro = {"Authorization": f"Bearer {token_membro}"}
    headers_admin = {"Authorization": f"Bearer {token_admin}"}

    # 3. Membro cria uma despesa
    print("\n[Membro] A registar despesa de 50.00 (Compra de Material)...")
    res_nova = requests.post(
        f"{BASE_URL}/transacoes/",
        json={"descricao": "Compra de Material", "valor": 50.00, "tipo": "despesa"},
        headers=headers_membro,
    )
    print("Status Criação:", res_nova.status_code)
    print("Resposta:", res_nova.json())

    # 4. Membro lista as suas transações
    print("\n[Membro] A listar as suas transações...")
    res_lista_membro = requests.get(f"{BASE_URL}/transacoes/", headers=headers_membro)
    print("Transações visíveis ao Membro:", res_lista_membro.json())

    # 5. Admin lista todas as transações da família
    print("\n[Admin] A inspecionar todas as transações da família...")
    res_lista_admin = requests.get(f"{BASE_URL}/transacoes/", headers=headers_admin)
    print("Transações globais (Admin):", res_lista_admin.json())

print("\n--- TESTES CONCLUÍDOS COM SUCESSO ---")
