"""Compra de ingressos pelo cliente, e o mapa de assentos.

O mapa é público: quem procura sessão precisa ver o que sobrou — e onde estão
os lugares acessíveis — antes de criar conta. Comprar, esse sim, exige login.
Ver decisões D10 e D16.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.core.deps import require_role
from app.db import get_db
from app.models.user import Role, User
from app.schemas.order import (
    OrderCreate,
    OrderOut,
    PaymentIn,
    SeatMapOut,
    TicketDetailOut,
    to_order_out,
    to_seat_map,
    to_ticket_detail,
)
from app.services.order_service import (
    DuplicateSeat,
    OrderNotFound,
    OrderNotPayable,
    OrderService,
    SeatDoesNotExist,
    SeatTaken,
    SessionNotAvailable,
)

# --------------------------------------------------------------------------
# Mapa de assentos (publico)
# --------------------------------------------------------------------------

mapa = APIRouter(prefix="/sessions", tags=["Sessões (público)"])


@mapa.get("/{session_id}/seats", response_model=SeatMapOut)
def seats(session_id: uuid.UUID, db: DbSession = Depends(get_db)) -> SeatMapOut:
    servico = OrderService(db)
    try:
        session = servico.session_on_sale(session_id)
    except SessionNotAvailable:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Sessão não encontrada ou não está mais à venda"
        )
    return to_seat_map(session, servico.taken_seats(session_id))


# --------------------------------------------------------------------------
# Compra (cliente)
# --------------------------------------------------------------------------

compra = APIRouter(
    prefix="/orders",
    tags=["Compra"],
    dependencies=[Depends(require_role(Role.CUSTOMER))],
)


def _as_http_error(error: Exception) -> HTTPException:
    if isinstance(error, SessionNotAvailable):
        return HTTPException(
            status.HTTP_404_NOT_FOUND, "Sessão não encontrada ou não está mais à venda"
        )
    if isinstance(error, SeatDoesNotExist):
        return HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Estas poltronas não existem nesta sala: {', '.join(error.codigos)}",
        )
    if isinstance(error, SeatTaken):
        return HTTPException(
            status.HTTP_409_CONFLICT,
            f"Estas poltronas acabaram de ser ocupadas: {', '.join(error.codigos)}",
        )
    if isinstance(error, DuplicateSeat):
        return HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "A mesma poltrona foi escolhida duas vezes"
        )
    if isinstance(error, OrderNotFound):
        return HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
    if isinstance(error, OrderNotPayable):
        return HTTPException(
            status.HTTP_409_CONFLICT, f"Este pedido não pode ser pago: {error.status.value}"
        )
    raise error


@compra.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def reservar(
    data: OrderCreate,
    user: User = Depends(require_role(Role.CUSTOMER)),
    db: DbSession = Depends(get_db),
) -> OrderOut:
    """Prende as poltronas e abre o pedido. Os assentos ficam presos por tempo
    limitado; sem pagamento, voltam ao estoque."""
    try:
        return to_order_out(OrderService(db).create(user.id, data))
    except Exception as e:
        raise _as_http_error(e)


@compra.post("/{order_id}/pay", response_model=OrderOut)
def pay(
    order_id: uuid.UUID,
    data: PaymentIn,
    user: User = Depends(require_role(Role.CUSTOMER)),
    db: DbSession = Depends(get_db),
) -> OrderOut:
    """Pagamento simulado. Aprovado emite os ingressos; recusado devolve as
    poltronas ao estoque. A regra dos cartões de teste está no README."""
    servico = OrderService(db)
    try:
        order = servico.pay(order_id, user.id, data.model_dump())
    except Exception as e:
        raise _as_http_error(e)
    return to_order_out(order, code_for=servico.code_for)


@compra.get("", response_model=list[OrderOut])
def meus_pedidos(
    user: User = Depends(require_role(Role.CUSTOMER)),
    db: DbSession = Depends(get_db),
) -> list[OrderOut]:
    servico = OrderService(db)
    return [
        to_order_out(p, code_for=servico.code_for)
        for p in servico.list_for_customer(user.id)
    ]


@compra.get("/{order_id}", response_model=OrderOut)
def detalhar_pedido(
    order_id: uuid.UUID,
    user: User = Depends(require_role(Role.CUSTOMER)),
    db: DbSession = Depends(get_db),
) -> OrderOut:
    servico = OrderService(db)
    try:
        return to_order_out(servico.get_for_customer(order_id, user.id), code_for=servico.code_for)
    except Exception as e:
        raise _as_http_error(e)


@compra.post("/{order_id}/cancel", response_model=OrderOut)
def cancel(
    order_id: uuid.UUID,
    user: User = Depends(require_role(Role.CUSTOMER)),
    db: DbSession = Depends(get_db),
) -> OrderOut:
    """Cancela o pedido e devolve as poltronas ao estoque."""
    try:
        return to_order_out(OrderService(db).cancel(order_id, user.id))
    except Exception as e:
        raise _as_http_error(e)


# --------------------------------------------------------------------------
# Meus ingressos (cliente)
# --------------------------------------------------------------------------

carteira = APIRouter(
    prefix="/me/tickets",
    tags=["Meus ingressos"],
    dependencies=[Depends(require_role(Role.CUSTOMER))],
)


@carteira.get("", response_model=list[TicketDetailOut])
def meus_ingressos(
    user: User = Depends(require_role(Role.CUSTOMER)),
    db: DbSession = Depends(get_db),
) -> list[TicketDetailOut]:
    servico = OrderService(db)
    return [
        to_ticket_detail(t, code=servico.code_for(t))
        for t in servico.tickets_for_customer(user.id)
    ]
