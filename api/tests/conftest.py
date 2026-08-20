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
from app.db import Base, get_db
from app.main import app as fastapi_app
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
