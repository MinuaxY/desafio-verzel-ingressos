"""Contratos de compra, ingresso e mapa de assentos.

Valores em centavos inteiros. Ver decisão D14.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.order import OrderStatus, TicketStatus
from app.models.room import SeatKind

MAX_ASSENTOS_POR_COMPRA = 10


# --------------------------------------------------------------------------
# Mapa de assentos
# --------------------------------------------------------------------------


class SeatOut(BaseModel):
    code: str
    taken: bool
    kind: SeatKind | None = None


class SectorMapOut(BaseModel):
    id: uuid.UUID
    name: str
    rows: int
    seats_per_row: int
    display_order: int
    price_cents: int
    aisles: list[int]
    seats: list[SeatOut]


class SeatMapOut(BaseModel):
    session_id: uuid.UUID
    movie_title: str
    starts_at: datetime
    room_name: str
    capacity: int
    available: int
    sectors: list[SectorMapOut]


# --------------------------------------------------------------------------
# Compra
# --------------------------------------------------------------------------


class SeatSelection(BaseModel):
    sector_id: uuid.UUID
    seat_code: str = Field(min_length=2, max_length=4)


class OrderCreate(BaseModel):
    session_id: uuid.UUID
    seats: list[SeatSelection] = Field(min_length=1, max_length=MAX_ASSENTOS_POR_COMPRA)


class PaymentIn(BaseModel):
    """Pagamento simulado.

    Não há transação financeira. O número do cartão decide o desfecho, como nos
    ambientes de teste dos provedores de verdade: qualquer número válido é
    aprovado, e um número específico é sempre recusado, para que a recusa possa
    ser demonstrada sem depender de sorte. A regra está no README.
    """

    card_number: str = Field(min_length=13, max_length=23, description="Número do cartão")
    card_holder: str = Field(min_length=2, max_length=80)


# --------------------------------------------------------------------------
# Saida
# --------------------------------------------------------------------------


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    seat_code: str
    sector_name: str
    seat_kind: SeatKind | None
    price_cents: int
    status: TicketStatus
    used_at: datetime | None

    # O código só acompanha ingresso pago: reserva não paga não tem QR.
    code: str | None = None
    share_token: uuid.UUID | None = None


class TicketDetailOut(TicketOut):
    """Ingresso com o contexto necessário para valer como documento."""

    movie_title: str
    movie_poster_url: str | None
    starts_at: datetime
    room_name: str
    room_location: str | None


class OrderOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    movie_title: str
    starts_at: datetime
    room_name: str
    status: OrderStatus
    total_cents: int
    created_at: datetime
    expires_at: datetime | None
    paid_at: datetime | None
    decline_reason: str | None
    tickets: list[TicketOut]


# --------------------------------------------------------------------------
# Portaria
# --------------------------------------------------------------------------


class GateCheckIn(BaseModel):
    code: str = Field(min_length=4, max_length=80, description="Conteúdo do QR ou digitado")
    session_id: uuid.UUID | None = Field(
        None,
        description="Sessão em que a portaria está trabalhando. "
        "Se informada, ingresso de outra sessão é recusado.",
    )


class GateResultOut(BaseModel):
    """As quatro respostas que o enunciado pede, mais o contexto para a tela.

    `result` é o que a portaria precisa saber num relance; `message` é o que se
    fala para a pessoa na fila.
    """

    result: str  # VALID | INVALID | ALREADY_USED | WRONG_SESSION
    message: str
    ticket: TicketDetailOut | None = None
    used_at: datetime | None = None


# --------------------------------------------------------------------------
# Conversao dos models para os contratos de saida.
# --------------------------------------------------------------------------


def _tipo_do_assento(ingresso) -> SeatKind | None:
    marcado = next(
        (s for s in ingresso.sector.special_seats if s.seat_code == ingresso.seat_code), None
    )
    return marcado.kind if marcado else None


def to_ticket_out(ingresso, *, codigo: str | None = None) -> TicketOut:
    return TicketOut(
        id=ingresso.id,
        seat_code=ingresso.seat_code,
        sector_name=ingresso.sector.name,
        seat_kind=_tipo_do_assento(ingresso),
        price_cents=ingresso.price_cents,
        status=ingresso.status,
        used_at=ingresso.used_at,
        code=codigo,
        share_token=ingresso.share_token if codigo else None,
    )


def to_ticket_detail(ingresso, *, codigo: str | None = None) -> TicketDetailOut:
    base = to_ticket_out(ingresso, codigo=codigo)
    sessao = ingresso.session
    return TicketDetailOut(
        **base.model_dump(),
        movie_title=sessao.movie_title,
        movie_poster_url=sessao.movie_poster_url,
        starts_at=sessao.starts_at,
        room_name=sessao.room.name,
        room_location=sessao.room.location,
    )


def to_order_out(pedido, *, codigo_de=None) -> OrderOut:
    sessao = pedido.session
    return OrderOut(
        id=pedido.id,
        session_id=pedido.session_id,
        movie_title=sessao.movie_title,
        starts_at=sessao.starts_at,
        room_name=sessao.room.name,
        status=pedido.status,
        total_cents=pedido.total_cents,
        created_at=pedido.created_at,
        expires_at=pedido.expires_at if pedido.status == OrderStatus.PENDING else None,
        paid_at=pedido.paid_at,
        decline_reason=pedido.decline_reason,
        tickets=[
            to_ticket_out(t, codigo=codigo_de(t) if codigo_de else None)
            for t in sorted(pedido.tickets, key=lambda t: (t.sector.display_order, t.seat_code))
        ],
    )


def to_seat_map(sessao, ocupados: set) -> SeatMapOut:
    precos = {p.sector_id: p.price_cents for p in sessao.prices}
    setores = []
    livres = 0

    for setor in sorted(sessao.room.sectors, key=lambda s: s.display_order):
        marcados = {a.seat_code: a.kind for a in setor.special_seats}
        assentos = []
        for codigo in setor.seat_codes:
            tomado = (setor.id, codigo) in ocupados
            livres += 0 if tomado else 1
            assentos.append(SeatOut(code=codigo, taken=tomado, kind=marcados.get(codigo)))

        setores.append(
            SectorMapOut(
                id=setor.id,
                name=setor.name,
                rows=setor.rows,
                seats_per_row=setor.seats_per_row,
                display_order=setor.display_order,
                price_cents=precos.get(setor.id, 0),
                aisles=sorted(setor.aisles or []),
                seats=assentos,
            )
        )

    return SeatMapOut(
        session_id=sessao.id,
        movie_title=sessao.movie_title,
        starts_at=sessao.starts_at,
        room_name=sessao.room.name,
        capacity=sessao.room.capacity,
        available=livres,
        sectors=setores,
    )
