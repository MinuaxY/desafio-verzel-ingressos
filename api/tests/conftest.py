"""Infraestrutura dos testes.

Roda contra um banco Postgres separado (verzel_test), criado e destruído a
cada sessão. Usar o mesmo SGBD da aplicação evita que um teste passe em
SQLite e quebre em produção por causa de enum nativo ou UUID.
"""
import os

os.environ["DATABASE_URL"] = "postgresql+psycopg://verzel:verzel@localhost:5432/verzel_test"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.core.security import hash_password
from app.db import Base, get_db
from app.main import app as fastapi_app
from app.models.user import Role, User
import app.models as _models  # noqa: F401  registra as tabelas

get_settings.cache_clear()

engine = create_engine(get_settings().database_url)
TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture(scope="session", autouse=True)
def schema():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def limpa_tabelas():
    """Cada teste começa com o banco vazio, para não depender da ordem."""
    yield
    with engine.begin() as conn:
        for tabela in reversed(Base.metadata.sorted_tables):
            conn.execute(tabela.delete())


@pytest.fixture
def client():
    def _get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    fastapi_app.dependency_overrides[get_db] = _get_db
    with TestClient(fastapi_app) as c:
        yield c
    fastapi_app.dependency_overrides.clear()


def cria_conta(client, dados: dict) -> dict[str, str]:
    """Cria a conta e devolve o cabeçalho de autorização.

    Cliente sai do cadastro público, que é o caminho real dele. Organizador e
    portaria não: o cadastro público só cria cliente, e esses papéis vêm do
    fluxo administrativo (`python -m app.admin`). Aqui o equivalente é gravar
    direto no banco.

    Nos dois casos o token vem do login normal, então o teste continua passando
    pelo mesmo caminho de entrada de quem usa o sistema. Ver decisão D34.
    """
    papel = Role(dados.get("role", Role.CUSTOMER.value))
    senha = dados["password"]

    if papel is Role.CUSTOMER:
        corpo = {c: v for c, v in dados.items() if c != "role"}
        resposta = client.post("/auth/register", json=corpo)
        return {"Authorization": f"Bearer {resposta.json()['access_token']}"}

    db = TestSession()
    try:
        db.add(
            User(
                name=dados["name"],
                email=dados["email"],
                password_hash=hash_password(senha),
                role=papel,
            )
        )
        db.commit()
    finally:
        db.close()

    entrou = client.post("/auth/login", json={"email": dados["email"], "password": senha})
    return {"Authorization": f"Bearer {entrou.json()['access_token']}"}
