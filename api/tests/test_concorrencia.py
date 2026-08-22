"""Duas pessoas disputando a mesma poltrona ao mesmo tempo.

Este é o teste que a decisão D5 existe para passar. A verificação de
disponibilidade feita na aplicação sempre tem uma janela: entre ler "está
livre" e gravar, outra requisição pode ter gravado. Quem fecha essa janela é o
índice único parcial no banco, não o código.

Threads de verdade, conexões de verdade, commits concorrentes. Um teste
sequencial não provaria nada aqui.
"""
import threading
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.catalog.factory import get_catalog_provider
from app.catalog.fixture import FixtureProvider
from app.config import get_settings
from app.models.order import Order, OrderStatus, Ticket, TicketStatus
from app.models.room import Room, Sector
from app.models.session import Session, SessionSectorPrice, SessionStatus
from app.models.user import Role, User
from app.schemas.order import OrderCreate, SeatSelection
from app.services.order_service import OrderService, SeatTaken

DISPUTANTES = 8


@pytest.fixture(autouse=True)
def usa_fixture_provider(monkeypatch):
    monkeypatch.setenv("CATALOG_PROVIDER", "fixture")
    monkeypatch.setenv("TMDB_READ_TOKEN", "")
    get_settings.cache_clear()
    get_catalog_provider.cache_clear()
    yield
    get_settings.cache_clear()
    get_catalog_provider.cache_clear()


@pytest.fixture
def engine_concorrente():
    """Engine própria: cada thread precisa da própria conexão."""
    motor = create_engine(get_settings().database_url, pool_size=DISPUTANTES + 2, max_overflow=4)
    yield motor
    motor.dispose()


@pytest.fixture
def arena(engine_concorrente):
    """Uma sessão publicada e vários clientes, todos de olho na mesma poltrona."""
    Sessao = sessionmaker(bind=engine_concorrente)
    db = Sessao()
    try:
        organizador = User(
            name="Org", email="org@conc.dev", password_hash="x", role=Role.ORGANIZER
        )
        clientes = [
            User(name=f"C{i}", email=f"c{i}@conc.dev", password_hash="x", role=Role.CUSTOMER)
            for i in range(DISPUTANTES)
        ]
        db.add_all([organizador, *clientes])
        db.flush()

        sala = Room(
            organizer_id=organizador.id,
            name="Arena",
            sectors=[Sector(name="Plateia", rows=2, seats_per_row=4)],
        )
        db.add(sala)
        db.flush()

        filme = FixtureProvider().items[0]
        sessao = Session(
            organizer_id=organizador.id,
            room_id=sala.id,
            catalog_id=filme.id,
            movie_title=filme.title,
            starts_at=datetime.now(timezone.utc) + timedelta(days=3),
            status=SessionStatus.PUBLISHED,
            prices=[SessionSectorPrice(sector_id=sala.sectors[0].id, price_cents=3000)],
        )
        db.add(sessao)
        db.commit()

        dados = {
            "session_id": sessao.id,
            "sector_id": sala.sectors[0].id,
            "clientes": [c.id for c in clientes],
        }
    finally:
        db.close()

    return dados


def _disputar(engine, arena, cliente_id, assento, largada, resultados, indice):
    Sessao = sessionmaker(bind=engine)
    db = Sessao()
    try:
        pedido = OrderCreate(
            session_id=arena["session_id"],
            seats=[SeatSelection(sector_id=arena["sector_id"], seat_code=assento)],
        )
        largada.wait()  # todas as threads partem juntas
        try:
            OrderService(db).criar(cliente_id, pedido)
            resultados[indice] = "comprou"
        except SeatTaken:
            resultados[indice] = "recusado"
        except Exception as e:  # pragma: no cover - só aparece se algo escapar
            resultados[indice] = f"erro inesperado: {type(e).__name__}: {e}"
    finally:
        db.close()


def test_apenas_um_leva_a_poltrona(engine_concorrente, arena):
    """Oito compras simultâneas na mesma poltrona: exatamente uma vence."""
    largada = threading.Barrier(DISPUTANTES)
    resultados: list[str | None] = [None] * DISPUTANTES

    threads = [
        threading.Thread(
            target=_disputar,
            args=(engine_concorrente, arena, arena["clientes"][i], "A1", largada, resultados, i),
        )
        for i in range(DISPUTANTES)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    inesperados = [r for r in resultados if r and r.startswith("erro")]
    assert not inesperados, f"exceções que escaparam: {inesperados}"

    assert resultados.count("comprou") == 1, resultados
    assert resultados.count("recusado") == DISPUTANTES - 1, resultados


def test_o_banco_tem_um_unico_ingresso_para_a_poltrona(engine_concorrente, arena):
    largada = threading.Barrier(DISPUTANTES)
    resultados: list[str | None] = [None] * DISPUTANTES

    threads = [
        threading.Thread(
            target=_disputar,
            args=(engine_concorrente, arena, arena["clientes"][i], "A2", largada, resultados, i),
        )
        for i in range(DISPUTANTES)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    Sessao = sessionmaker(bind=engine_concorrente)
    db = Sessao()
    try:
        ocupando = db.scalars(
            select(Ticket).where(
                Ticket.session_id == arena["session_id"],
                Ticket.seat_code == "A2",
                Ticket.status != TicketStatus.CANCELLED,
            )
        ).all()
        assert len(ocupando) == 1

        # Nenhum pedido fantasma: quem perdeu não deixou pedido pendente para trás.
        pendentes = db.scalars(
            select(Order).where(
                Order.session_id == arena["session_id"], Order.status == OrderStatus.PENDING
            )
        ).all()
        assert len(pendentes) == 1
    finally:
        db.close()


def test_poltronas_diferentes_nao_se_atrapalham(engine_concorrente, arena):
    """A trava é por poltrona, não por sessão: oito pessoas comprando lugares
    distintos ao mesmo tempo devem todas conseguir."""
    largada = threading.Barrier(DISPUTANTES)
    resultados: list[str | None] = [None] * DISPUTANTES
    assentos = ["A1", "A2", "A3", "A4", "B1", "B2", "B3", "B4"]

    threads = [
        threading.Thread(
            target=_disputar,
            args=(
                engine_concorrente, arena, arena["clientes"][i], assentos[i],
                largada, resultados, i,
            ),
        )
        for i in range(DISPUTANTES)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert resultados.count("comprou") == DISPUTANTES, resultados
