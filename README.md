# Família Vieira Agostini — Sistema de Gestão Financeira

Aplicação web para registar e consultar receitas e despesas de uma família. O
backend disponibiliza uma API REST em FastAPI, com persistência SQLAlchemy e
SQLite para desenvolvimento local. O frontend é uma página estática responsiva
que apresenta o histórico e resumos financeiros.

## Demonstração do sistema

O fluxo demonstrável é: abrir a página local, criar uma conta de membro ou
iniciar sessão, registar receitas e despesas e consultar o histórico e os
resumos disponíveis para o perfil autenticado. A API também disponibiliza um
resumo familiar reservado a administradores.

Este repositório não contém capturas de ecrã: os ficheiros
`assets/dashboard.png` e `assets/shortcut-ios.png` não estão disponíveis, por
isso não são apresentados como imagens. Também não existe integração com
Atalhos iOS.

## Funcionalidades implementadas

- Cadastro de membros e autenticação com tokens JWT.
- Registo de receitas e despesas com categorias e métodos de pagamento.
- Consulta de transações com filtros por período.
- Resumos de receitas, despesas, saldo e despesas em cartão de crédito.
- Gráficos de despesas por categoria e, para administradores, totais por
  membro.
- Exportação do histórico acessível pelo utilizador para um ficheiro JSON.
- Controlo de permissões no backend: membros acedem apenas às próprias
  transações; administradores podem consultar dados familiares e usar as
  categorias restritas.

## Tecnologias e arquitetura

```text
Navegador
  └── frontend/index.html (HTML, CSS/Tailwind e JavaScript)
        ├── Gráficos Chart.js
        └── pedidos HTTP autenticados
                 │
                 ▼
         backend/main.py (FastAPI)
           ├── JWT e autorização por perfil
           ├── validação Pydantic
           └── consultas SQLAlchemy
                    │
                    ▼
         backend/database.py
                    │
                    ▼
              SQLite local
       financeiro_familiar.db
```

O frontend e a API são processos separados. A API é servida pelo Uvicorn; a
página estática é servida à parte por um servidor HTTP. Tailwind CSS e Chart.js
são carregados de CDNs no navegador, pelo que a interface precisa de ligação à
internet para obter essas bibliotecas. Este repositório não contém `package.json`
nem um pipeline de build Node.

### Estrutura do repositório

| Caminho | Responsabilidade |
| --- | --- |
| `backend/main.py` | Aplicação, rotas, autenticação, autorização e consultas. |
| `backend/database.py` | Engine, sessões e configuração SQLAlchemy via `DATABASE_URL`. |
| `backend/models.py` | Modelos ORM de utilizadores e transações. |
| `backend/schemas.py` | Validação Pydantic dos pedidos e respostas. |
| `frontend/index.html` | Interface, gráficos, formulários e integração com a API. |
| `tests/` | Testes automatizados da API e do contrato básico do frontend. |
| `testar_sistema.py` | Teste manual de integração contra uma API já iniciada. |
| `requirements.txt` | Dependências Python com versões fixadas. |
| `.env.example` | Exemplo de nomes de variáveis e valores não secretos. |
| `wireframes.txt` | Esboços textuais da interface. |

### Dados e permissões

| Tabela | Campos principais | Finalidade |
| --- | --- | --- |
| `usuarios` | `id`, `nome`, `email`, `senha_hash`, `tipo` | Contas de utilizador com perfil `membro` ou `admin`. |
| `transacoes` | `id`, `descricao`, `valor`, `tipo`, `categoria`, `categoria_detalhe`, `metodo_pagamento`, `data`, `usuario_id` | Receitas e despesas associadas à conta que as registou. |

As palavras-passe são guardadas como hashes bcrypt, não em texto simples. O
cadastro público cria apenas contas `membro`; não existe rota pública para
promover uma conta a `admin`. As categorias `Moradia` e `Contas Fixas` e o
resumo familiar são reservados a administradores. A autorização é verificada
pela API e não depende da visibilidade dos controlos no frontend.

No arranque da aplicação, o SQLAlchemy cria tabelas em falta. Também são
acrescentadas à tabela `transacoes` colunas legadas para categoria, detalhe e
método de pagamento, quando necessário. Estas alterações não apagam os registos
existentes; ainda assim, faça cópia de segurança antes de iniciar a aplicação
com uma base que contenha dados importantes. O projeto não usa Alembic nem
dispõe de um sistema geral de migrações.

## Requisitos

- Python 3.10 ou superior.
- `pip`.
- Ligação à internet para instalar dependências e carregar Tailwind CSS e
  Chart.js no navegador.
- PowerShell no Windows ou Bash num sistema macOS/Linux.

SQLite e o respetivo driver vêm com o Python. As dependências da API, do teste
manual e da suíte automatizada estão fixadas em `requirements.txt`.

## Instalação e execução local

Execute os comandos a partir da raiz do repositório. O processo da API e o
servidor estático do frontend devem permanecer ativos em terminais separados.
O backend não carrega ficheiros `.env` automaticamente: defina as variáveis no
ambiente do processo que inicia o Uvicorn.

### Windows (PowerShell)

1. Crie um ambiente virtual e instale as dependências:

   ```powershell
   py -3 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install --upgrade pip
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

2. No terminal da API, configure uma chave JWT aleatória e a base SQLite:

   ```powershell
   $env:SECRET_KEY = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
   $env:DATABASE_URL = "sqlite:///./financeiro_familiar.db"
   $env:FRONTEND_ORIGINS = "http://127.0.0.1:5500,http://localhost:5500"
   ```

   Mantenha este terminal aberto. As variáveis `$env:` são locais à sessão do
   PowerShell. Gere outra chave privada para cada ambiente e não a inclua no
   Git.

3. Inicie a API no mesmo terminal:

   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
   ```

4. Abra outro terminal na raiz e sirva o frontend:

   ```powershell
   py -m http.server 5500 --directory frontend
   ```

5. Aceda à interface em <http://127.0.0.1:5500>. A documentação interativa da
   API está em <http://127.0.0.1:8000/docs> e o esquema OpenAPI em
   <http://127.0.0.1:8000/openapi.json>.

### macOS e Linux

Na raiz do projeto, crie o ambiente virtual e instale as dependências:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

No terminal da API, configure o ambiente e inicie o backend:

```bash
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export DATABASE_URL="sqlite:///./financeiro_familiar.db"
export FRONTEND_ORIGINS="http://127.0.0.1:5500,http://localhost:5500"
python -m uvicorn backend.main:app --reload
```

Num segundo terminal, na raiz do projeto, sirva a página:

```bash
python3 -m http.server 5500 --directory frontend
```

Abra <http://127.0.0.1:5500>. As variáveis de ambiente precisam de ser
redefinidas quando iniciar uma nova sessão de terminal.

### Configuração do frontend e da base de dados

A URL da API no frontend é configurada pelo elemento `meta` `api-base-url` no
`frontend/index.html`. O valor padrão é `http://127.0.0.1:8000`; altere-o para o
endereço público correto ao servir a página noutro ambiente. Configure
`FRONTEND_ORIGINS` no backend com as origens exatas em que a página será
servida, separadas por vírgulas.

Para o SQLite local, `DATABASE_URL` deve ser
`sqlite:///./financeiro_familiar.db`. O caminho relativo é resolvido a partir
do diretório de trabalho do processo, por isso inicie o Uvicorn na raiz do
repositório. O ficheiro da base de dados é ignorado pelo Git.

O ficheiro `.env.example` serve de referência; copiar ou editar esse ficheiro
não configura o processo. Para outro motor SQLAlchemy, configure a URL e o
driver correspondentes. O projeto inclui PyMySQL para URLs MySQL, mas a
instalação e os comandos documentados neste README usam SQLite.

## API

| Método | Rota | Autenticação | Descrição |
| --- | --- | --- | --- |
| `POST` | `/usuarios/` | Pública | Cria uma conta de perfil `membro`. |
| `POST` | `/token` | Formulário OAuth2 | Recebe e-mail em `username` e palavra-passe em `password`; devolve JWT. |
| `POST` | `/transacoes/` | Bearer | Cria uma transação para a conta autenticada. |
| `GET` | `/transacoes/` | Bearer | Lista transações; aceita `inicio`, `fim` e `member_id`, conforme as permissões. |
| `GET` | `/transacoes/resumo-membros` | Bearer, apenas admin | Devolve despesas agregadas por membro; aceita `inicio` e `fim`. |

Categorias aceites: `Alimentação`, `Moradia`, `Transporte`, `Lazer`, `Salário`,
`Contas Gerais` e `Contas Fixas`. Métodos de pagamento aceites: `Dinheiro`,
`Débito` e `Cartão de Crédito`. Descrição, valor, tipo, categoria e método são
validados pela API; datas dos filtros usam `AAAA-MM-DD`. Os pedidos inválidos
recebem HTTP `422`, credenciais ausentes ou inválidas HTTP `401`, operações sem
permissão HTTP `403` e intervalos de datas invertidos HTTP `400`.

Para uma rota protegida, envie o token devolvido por `/token` no cabeçalho:

```text
Authorization: Bearer <access_token>
```

## Testes

A suíte automatizada usa uma base SQLite em memória separada da base local e
cria dados fictícios por teste. Não requer credenciais externas:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Em macOS/Linux, com o ambiente virtual ativo:

```bash
python -m pytest -q
```

`testar_sistema.py` é um teste de integração opcional contra uma API já
iniciada. Requer contas descartáveis previamente cadastradas e variáveis de
ambiente próprias para membro e administrador; cria uma transação fictícia na
base configurada e não a remove automaticamente. Não o execute contra dados de
produção. No PowerShell, defina os dados das contas de teste e execute:

```powershell
$env:TEST_BASE_URL = "http://127.0.0.1:8000"
$env:TEST_MEMBER_EMAIL = "membro-de-teste@example.com"
$env:TEST_MEMBER_PASSWORD = "substitua-pela-senha-da-conta-descartavel"
$env:TEST_ADMIN_EMAIL = "admin-de-teste@example.com"
$env:TEST_ADMIN_PASSWORD = "substitua-pela-senha-da-conta-descartavel"
.\.venv\Scripts\python.exe .\testar_sistema.py
```

O cadastro HTTP cria apenas membros; a conta administrativa precisa de ser
provisionada por um operador autorizado. Não reutilize palavras-passe pessoais
nestes testes.

## Segurança, dados pessoais e limitações

- `SECRET_KEY` é obrigatória e deve ser aleatória, privada e diferente por
  ambiente. O backend não fornece uma chave fixa nem lê automaticamente `.env`.
- CORS permite por padrão apenas `localhost:5500` e `127.0.0.1:5500`. Configure
  `FRONTEND_ORIGINS` com origens específicas ao alterar a origem do frontend.
- Os tokens expiram após 24 horas. O frontend mantém o token no `localStorage`
  do navegador; use HTTPS e proteja o dispositivo em ambientes não locais.
- A base SQLite contém potencialmente dados financeiros pessoais. Não a
  publique, não a inclua em backups partilhados sem proteção e restrinja o
  acesso aos seus ficheiros.
- Uvicorn com `--reload` e `python -m http.server` são opções de
  desenvolvimento, não uma configuração de produção. O repositório não define
  um processo de deploy, HTTPS, criação inicial de administradores ou migrações
  avançadas.
- Os valores monetários são persistidos como `Float`; para contabilidade de
  produção, uma migração para decimal de precisão fixa exige definir previamente
  a escala e a regra de conversão dos registos existentes.
- Não há limitação de tentativas de login nem política automatizada de backups.
- O repositório não inclui capturas de ecrã nem uma integração de Atalhos iOS.

## Status do projeto

O estado atual é adequado para demonstração e desenvolvimento local. A suíte
automatizada e a inicialização SQLite são verificadas, mas isto não constitui
certificação ou preparação para produção. Antes de gerir dados financeiros
reais, é necessário definir precisão monetária e conversão segura dos dados,
além de preparar e validar deploy, HTTPS, backups, limitação de tentativas de
login e um processo de migrações apropriado.

## Assistência de Inteligência Artificial

O desenvolvimento deste projeto contou com assistência de ferramentas de
Inteligência Artificial. A assistência não substitui a revisão humana: o
código, as dependências, as configurações de segurança e os resultados devem
ser analisados, testados e validados pelos responsáveis do projeto antes da
utilização ou publicação.
