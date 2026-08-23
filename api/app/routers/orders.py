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
def assentos(session_id: uuid.UUID, db: DbSession = Depends(get_db)) -> SeatMapOut:
    servico = OrderService(db)
    try:
        sessao = servico.sessao_a_venda(session_id)
    except SessionNotAvailable:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Sessão não encontrada ou não está mais à venda"
        )
    return to_seat_map(sessao, servico.assentos_ocupados(session_id))


# --------------------------------------------------------------------------
# Compra (cliente)
# --------------------------------------------------------------------------

compra = APIRouter(
    prefix="/orders",
    tags=["Compra"],
    dependencies=[Depends(require_role(Role.CUSTOMER))],
)


def _traduz(erro: Exception) -> HTTPException:
    if isinstance(erro, SessionNotAvailable):
        return HTTPException(
            status.HTTP_404_NOT_FOUND, "Sessão não encontrada ou não está mais à venda"
        )
    if isinstance(erro, SeatDoesNotExist):
        return HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Estas poltronas não existem nesta sala: {', '.join(erro.codigos)}",
        )
    if isinstance(erro, SeatTaken):
        return HTTPException(
            status.HTTP_409_CONFLICT,
            f"Estas poltronas acabaram de ser ocupadas: {', '.join(erro.codigos)}",
        )
    if isinstance(erro, DuplicateSeat):
        return HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "A mesma poltrona foi escolhida duas vezes"
        )
    if isinstance(erro, OrderNotFound):
        return HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
    if isinstance(erro, OrderNotPayable):
        return HTTPException(
            status.HTTP_409_CONFLICT, f"Este pedido não pode ser pago: {erro.status.value}"
        )
    raise erro


@compra.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def reservar(
    dados: OrderCreate,
    user: User = Depends(require_role(Role.CUSTOMER)),
    db: DbSession = Depends(get_db),
) -> OrderOut:
    """Prende as poltronas e abre o pedido. Os assentos ficam presos por tempo
    limitado; sem pagamento, voltam ao estoque."""
    try:
        return to_order_out(OrderService(db).criar(user.id, dados))
    except Exception as e:
        raise _traduz(e)


@compra.post("/{order_id}/pay", response_model=OrderOut)
def pagar(
    order_id: uuid.UUID,
    dados: PaymentIn,
    user: User = Depends(require_role(Role.CUSTOMER)),
    db: DbSession = Depends(get_db),
) -> OrderOut:
    """Pagamento simulado. Aprovado emite os ingressos; recusado devolve as
    poltronas ao estoque. A regra dos cartões de teste está no README."""
    servico = OrderService(db)
    try:
        pedido = servico.pagar(order_id, user.id, dados.model_dump())
    except Exception as e:
        raise _traduz(e)
    return to_order_out(pedido, codigo_de=servico.codigo_do)


@compra.get("", response_model=list[OrderOut])
def meus_pedidos(
    user: User = Depends(require_role(Role.CUSTOMER)),
    db: DbSession = Depends(get_db),
) -> list[OrderOut]:
    servico = OrderService(db)
    return [
        to_order_out(p, codigo_de=servico.codigo_do)
        for p in servico.listar_do_cliente(user.id)
    ]


@compra.get("/{order_id}", response_model=OrderOut)
def detalhar_pedido(
    order_id: uuid.UUID,
    user: User = Depends(require_role(Role.CUSTOMER)),
    db: DbSession = Depends(get_db),
) -> OrderOut:
    servico = OrderService(db)
    try:
        return to_order_out(servico.obter(order_id, user.id), codigo_de=servico.codigo_do)
    except Exception as e:
        raise _traduz(e)


@compra.post("/{order_id}/cancel", response_model=OrderOut)
def cancelar(
    order_id: uuid.UUID,
    user: User = Depends(require_role(Role.CUSTOMER)),
    db: DbSession = Depends(get_db),
) -> OrderOut:
    """Cancela o pedido e devolve as poltronas ao estoque."""
    try:
        return to_order_out(OrderService(db).cancelar(order_id, user.id))
    except Exception as e:
        raise _traduz(e)


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
        to_ticket_detail(t, codigo=servico.codigo_do(t))
        for t in servico.ingressos_do_cliente(user.id)
    ]
