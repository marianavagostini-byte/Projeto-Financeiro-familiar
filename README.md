# Família Vieira Agostini — Sistema de Gestão Financeira

Aplicação web para registar, consultar e acompanhar receitas e despesas da
família. A API é desenvolvida com FastAPI, os dados locais podem ser guardados
em SQLite e a interface apresenta resumos, gráficos e histórico de transações.
Atalhos iOS podem comunicar com a API através dos endpoints HTTP existentes;
para acesso remoto durante desenvolvimento, é possível expor a API com ngrok.

> **Estado da integração iOS:** a rota `POST /api/webhook/transacao` não está
> implementada. Um Atalho pode chamar os endpoints existentes (`/token` e
> `/transacoes/`), mas requer autenticação Bearer e o formato de dados descrito
> abaixo.

## Funcionalidades

- Registo de utilizadores e autenticação por token JWT.
- Registo de receitas e despesas com categoria e método de pagamento.
- Resumo de saldo, receitas, despesas e gastos no cartão de crédito.
- Filtro de transações por período e exportação do histórico acessível em JSON.
- Gráficos de despesas por categoria e, para administradores, por membro.
- Controlo de acesso: categorias “Moradia” e “Contas Fixas”, o resumo familiar e
  a consulta de transações de outros utilizadores são reservados a
  administradores.

## Arquitetura

```text
Frontend (frontend/index.html)
  ├── interface responsiva em modo escuro
  ├── gráficos Chart.js
  └── pedidos HTTP com token Bearer
          │
          ▼
API FastAPI (backend/main.py)
  ├── autenticação e autorização
  ├── validação Pydantic (backend/schemas.py)
  └── persistência SQLAlchemy
          │
          ▼
Base de dados SQLite (local) ou outro banco configurado
  ├── usuarios
  └── transacoes

Atalhos iOS ── HTTP ──► API FastAPI
                         └── ngrok opcional para túnel de desenvolvimento
```

O backend lê `DATABASE_URL` e `SECRET_KEY` do ambiente. Na configuração local
abaixo, a base SQLite é criada como `financeiro_familiar.db` na raiz do projeto.
Ao iniciar, o backend cria as tabelas e adiciona às tabelas de transações as
colunas de categoria e método de pagamento, caso ainda não existam.

## Requisitos

- Windows 10/11 e PowerShell.
- Python 3.10 ou superior.
- Ligação à internet para descarregar as dependências e as bibliotecas
  JavaScript carregadas pelo frontend.
- [ngrok](https://ngrok.com/) apenas se precisar de acesso remoto à API.

## Executar localmente no Windows

Abra um PowerShell na pasta raiz do repositório:

```powershell
Set-Location "C:\caminho\para\Projeto-Financeiro"
```

### 1. Criar o ambiente e instalar as dependências

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install "fastapi" "uvicorn[standard]" "sqlalchemy" "python-jose[cryptography]" "passlib[bcrypt]" "python-multipart" "email-validator" "requests"
```

### 2. Configurar o backend

Defina uma chave aleatória para assinar os tokens e selecione SQLite:

```powershell
$env:SECRET_KEY = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
$env:DATABASE_URL = "sqlite:///./financeiro_familiar.db"
```

Mantenha esta janela aberta: as variáveis de ambiente são válidas para esta
sessão do PowerShell.

### 3. Iniciar a API

Na mesma janela:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

A API estará disponível em `http://127.0.0.1:8000`. A documentação interativa
do FastAPI encontra-se em `http://127.0.0.1:8000/docs`.

### 4. Iniciar o frontend

Abra **uma segunda janela** do PowerShell na raiz do projeto e execute:

```powershell
Set-Location "C:\caminho\para\Projeto-Financeiro"
py -m http.server 5500 --directory frontend
```

Abra `http://127.0.0.1:5500` no navegador. Para encerrar cada servidor,
pressione `Ctrl+C` na respetiva janela.

> A interface aponta a API para `http://127.0.0.1:8000`. Se alterar o endereço
> ou a porta da API, atualize `API_URL` em `frontend/index.html`.

## Base de dados

### SQLite

Use esta configuração para desenvolvimento local:

```powershell
$env:DATABASE_URL = "sqlite:///./financeiro_familiar.db"
```

O ficheiro `financeiro_familiar.db` é criado na raiz do projeto quando o
backend inicia. O `.gitignore` exclui ficheiros `*.db`; não os adicione ao
controlo de versões se contiverem dados pessoais.

### Estrutura básica

| Tabela | Campos principais | Finalidade |
| --- | --- | --- |
| `usuarios` | `id`, `nome`, `email`, `senha_hash`, `tipo` | Contas da família e perfil (`membro` ou `admin`). |
| `transacoes` | `id`, `descricao`, `valor`, `tipo`, `categoria`, `categoria_detalhe`, `metodo_pagamento`, `data`, `usuario_id` | Movimentos financeiros associados ao utilizador que os registou. |

`usuario_id` referencia `usuarios.id`. A aplicação guarda hashes de palavras
passe, não a palavra-passe original. As novas colunas de transação têm valores
predefinidos para permitir a leitura dos registos existentes.

O registo público cria contas com perfil `membro`. Não existe atualmente um
endpoint para promover uma conta a administrador; a atribuição inicial desse
perfil deve ser feita por um operador autorizado diretamente na base de dados.

## Endpoints principais

| Método | Rota | Autenticação | Descrição |
| --- | --- | --- | --- |
| `POST` | `/usuarios/` | Não | Cria uma conta com perfil de membro. |
| `POST` | `/token` | Não | Autentica com `username` e `password` em formulário e devolve JWT. |
| `POST` | `/transacoes/` | Bearer | Regista uma transação. |
| `GET` | `/transacoes/` | Bearer | Lista transações; aceita `inicio`, `fim` e `member_id` conforme o perfil. |
| `GET` | `/transacoes/resumo-membros` | Bearer, apenas admin | Devolve despesas agrupadas por utilizador; aceita `inicio` e `fim`. |

Exemplo do corpo JSON de `POST /transacoes/`:

```json
{
  "descricao": "Compras de supermercado",
  "valor": 125.5,
  "tipo": "despesa",
  "categoria": "Alimentação",
  "metodo_pagamento": "Cartão de Crédito"
}
```

Categorias aceites: `Alimentação`, `Moradia`, `Transporte`, `Lazer`, `Salário`,
`Contas Gerais` e `Contas Fixas`. Métodos de pagamento aceites: `Dinheiro`,
`Débito` e `Cartão de Crédito`. “Moradia” e “Contas Fixas” só podem ser
registadas por administradores.

Para criar uma transação por HTTP, obtenha primeiro um token em `/token` e
envie-o no cabeçalho `Authorization: Bearer <token>`. As respostas de validação
de pedidos inválidos do FastAPI usam normalmente HTTP `422`; pedidos sem
autenticação válida recebem HTTP `401`.

## Atalhos iOS e acesso remoto com ngrok

Os Atalhos iOS podem usar a ação **Obter conteúdo do URL** para enviar pedidos
HTTP à API. Um fluxo típico autentica em `POST /token`, guarda o
`access_token` durante a execução do Atalho e envia-o como `Bearer` em
`POST /transacoes/`.

Para testes remotos, com a API local em execução, inicie o túnel numa terceira
janela do PowerShell:

```powershell
ngrok http 8000
```

Use no Atalho o endereço HTTPS atribuído pelo ngrok, seguido da rota da API.
O endereço público pode mudar entre sessões. Proteja o token de autenticação e
não partilhe o endereço do túnel sem necessidade. **A rota
`/api/webhook/transacao` não existe nesta versão**; os pedidos devem usar os
endpoints documentados.

## Testes manuais da API

Com a API em execução, pode testar uma rota sem autenticação no PowerShell:

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/docs"
```

O script `testar_sistema.py` exercita login e operações de transação. Antes de
o executar, crie contas de teste na base local e defina as respetivas
credenciais no PowerShell:

```powershell
$env:TEST_BASE_URL = "http://127.0.0.1:8000"
$env:TEST_MEMBER_EMAIL = "membro-de-teste@example.com"
$env:TEST_MEMBER_PASSWORD = "palavra-passe-de-teste"
$env:TEST_ADMIN_EMAIL = "admin-de-teste@example.com"
$env:TEST_ADMIN_PASSWORD = "outra-palavra-passe-de-teste"
.\.venv\Scripts\python.exe .\testar_sistema.py
```

O script cria uma transação de exemplo quando ambas as autenticações são
bem-sucedidas; use apenas contas e dados de desenvolvimento.

## Segurança e configuração

- Gere uma `SECRET_KEY` diferente por ambiente e mantenha-a privada.
- `DATABASE_URL`, `SECRET_KEY` e credenciais de teste são variáveis de ambiente;
  consulte `.env.example` para os nomes esperados. O projeto não carrega
  automaticamente um ficheiro `.env`.
- O `.gitignore` exclui `.env`, `.venv/`, a cache do Python e bases `*.db`.
- A configuração atual de CORS permite qualquer origem e destina-se a
  desenvolvimento; restrinja-a antes de disponibilizar o serviço publicamente.
- O servidor `uvicorn --reload`, a interface de desenvolvimento e um túnel
  ngrok não substituem uma configuração de produção.

## Assistência de Inteligência Artificial

Este projeto foi desenvolvido com assistência de ferramentas de Inteligência
Artificial. O código, as configurações e as recomendações devem ser revistos e
validados pelos responsáveis do projeto antes de utilização ou publicação.
