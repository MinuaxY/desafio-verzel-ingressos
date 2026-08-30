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
    order_id: uuid.UUID
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
    # Distingue "eu desisti" de "o cinema cancelou". A tela precisa disso para
    # não deixar o cliente achar que a desistência foi dele. Ver decisão D30.
    cancelled_by_organizer: bool
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


def _seat_kind_of(ticket) -> SeatKind | None:
    marcado = next(
        (s for s in ticket.sector.special_seats if s.seat_code == ticket.seat_code), None
    )
    return marcado.kind if marcado else None


def to_ticket_out(ticket, *, code: str | None = None) -> TicketOut:
    return TicketOut(
        id=ticket.id,
        order_id=ticket.order_id,
        seat_code=ticket.seat_code,
        sector_name=ticket.sector.name,
        seat_kind=_seat_kind_of(ticket),
        price_cents=ticket.price_cents,
        status=ticket.status,
        used_at=ticket.used_at,
        code=code,
        share_token=ticket.share_token if code else None,
    )


def to_ticket_detail(ticket, *, code: str | None = None) -> TicketDetailOut:
    base = to_ticket_out(ticket, code=code)
    session = ticket.session
    return TicketDetailOut(
        **base.model_dump(),
        movie_title=session.movie_title,
        movie_poster_url=session.movie_poster_url,
        starts_at=session.starts_at,
        room_name=session.room.name,
        room_location=session.room.location,
    )


def to_order_out(order, *, code_for=None) -> OrderOut:
    session = order.session
    return OrderOut(
        id=order.id,
        session_id=order.session_id,
        movie_title=session.movie_title,
        starts_at=session.starts_at,
        room_name=session.room.name,
        status=order.status,
        total_cents=order.total_cents,
        created_at=order.created_at,
        expires_at=order.expires_at if order.status == OrderStatus.PENDING else None,
        paid_at=order.paid_at,
        decline_reason=order.decline_reason,
        cancelled_by_organizer=order.cancelled_by_organizer,
        tickets=[
            to_ticket_out(t, code=code_for(t) if code_for else None)
            for t in sorted(order.tickets, key=lambda t: (t.sector.display_order, t.seat_code))
        ],
    )


def to_seat_map(session, occupied: set) -> SeatMapOut:
    prices = {p.sector_id: p.price_cents for p in session.prices}
    sectors = []
    livres = 0

    for sector in sorted(session.room.sectors, key=lambda s: s.display_order):
        marcados = {a.seat_code: a.kind for a in sector.special_seats}
        seats = []
        for code in sector.seat_codes:
            tomado = (sector.id, code) in occupied
            livres += 0 if tomado else 1
            seats.append(SeatOut(code=code, taken=tomado, kind=marcados.get(code)))

        sectors.append(
            SectorMapOut(
                id=sector.id,
                name=sector.name,
                rows=sector.rows,
                seats_per_row=sector.seats_per_row,
                display_order=sector.display_order,
                price_cents=prices.get(sector.id, 0),
                aisles=sorted(sector.aisles or []),
                seats=seats,
            )
        )

    return SeatMapOut(
        session_id=session.id,
        movie_title=session.movie_title,
        starts_at=session.starts_at,
        room_name=session.room.name,
        capacity=session.room.capacity,
        available=livres,
        sectors=sectors,
    )
