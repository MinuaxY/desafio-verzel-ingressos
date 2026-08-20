# Verzel Ingressos

Plataforma de sessões de cinema e ingressos, desenvolvida para o Desafio Elite Dev.

O organizador cria sessões a partir do catálogo de filmes do TMDb, definindo data, sala,
capacidade e preço. O cliente escolhe o assento, paga de forma simulada e recebe um
ingresso com código em QR. Na entrada, a portaria valida o ingresso.

> 🚧 Em desenvolvimento — Sprint 1 de 5. Este README é atualizado a cada sprint.

## Stack

| Camada | Tecnologia |
|---|---|
| Front-end | React + Vite |
| Back-end | Python + FastAPI |
| Banco | PostgreSQL 16 |
| Catálogo externo | TMDb API |

## Como executar

Pré-requisitos: Docker, Python 3.11+ e Node 18+.

### 1. Banco de dados

```bash
docker compose up -d
```

Sobe o PostgreSQL na porta 5432. Aguarde o container ficar `healthy`.

### 2. API

```bash
cd api
python -m venv .venv
.venv/Scripts/activate        # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edite o `.env` e preencha `TMDB_READ_TOKEN` com o seu token de leitura do
[TMDb](https://www.themoviedb.org/settings/api). Em seguida:

```bash
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

A API sobe em `http://localhost:8000`. A documentação interativa fica em
`http://localhost:8000/docs`.

### 3. Front-end

Ainda não implementado — Sprint 1 em andamento.

## Usuários de teste

Criados pelo comando `python -m app.seed`. Senha de todos: `verzel123`.

| Papel | E-mail | O que pode fazer |
|---|---|---|
| Organizador | `organizador@verzel.dev` | Criar e gerenciar sessões |
| Cliente | `cliente1@verzel.dev` | Reservar, pagar e receber ingressos |
| Cliente | `cliente2@verzel.dev` | Idem |
| Portaria | `portaria@verzel.dev` | Validar ingressos na entrada |

## Testes

```bash
cd api
python -m pytest -v
```

Os testes rodam contra um banco separado (`verzel_test`), criado e destruído a cada
execução. O container do PostgreSQL precisa estar de pé.

## Documentação do processo

- [`docs/decisoes.md`](docs/decisoes.md) — decisões técnicas e o que foi descartado
- `docs/ia.md` — ferramentas de IA utilizadas e o que foi feito sem elas *(Sprint 5)*

## Estado atual

**Pronto:** autenticação com três papéis, autorização por papel, seed, migrations, 13 testes.
**Em andamento:** integração com o catálogo TMDb e interface do front-end.
