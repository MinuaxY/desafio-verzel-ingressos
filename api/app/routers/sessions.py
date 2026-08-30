"""Sessões de cinema.

A vitrine é **pública**: quem ainda não tem conta consegue ver o que está em
cartaz, como em qualquer site de ingressos. A autenticação é exigida na hora
de reservar, não na hora de olhar. Ver decisão D10.

A gestão, essa sim, é do organizador.
"""
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session as DbSession

from app.core.deps import require_role
from app.db import get_db
from app.models.user import Role, User
from app.schemas.session import (
    BatchResult,
    DayInCartaz,
    OrdersCancelled,
    SessionCreate,
    SessionOut,
    SessionPage,
    SessionRepeat,
    SessionUpdate,
    SkippedDate,
    to_list_item,
    to_session_out,
)
from app.services.room_service import RoomNotFound
from app.services.session_service import (
    MovieNotFound,
    PricesDoNotCoverSectors,
    RoomBusy,
    SessionAlreadyCancelled,
    SessionHasTickets,
    SessionInThePast,
    SessionIsPublished,
    SessionNotFound,
    SessionService,
    SessionSold,
)

# --------------------------------------------------------------------------
# Vitrine publica
# --------------------------------------------------------------------------

publico = APIRouter(prefix="/sessions", tags=["Sessões (público)"])


@publico.get("/days", response_model=list[DayInCartaz])
def days_on_billboard(
    days: int = Query(14, ge=1, le=60, description="Quantos dias olhar para a frente"),
    search: str | None = Query(None),
    db: DbSession = Depends(get_db),
) -> list[DayInCartaz]:
    """Dias que têm sessão, para a barra de datas da vitrine.

    Declarado antes de `/{session_id}` de propósito: o roteador casa na ordem,
    e "days" seria capturado como se fosse um id.
    """
    contagem = SessionService(db).days_on_billboard(days=days, search=search)
    return [DayInCartaz(date=d, total=t) for d, t in sorted(contagem.items())]


@publico.get("", response_model=SessionPage)
def list_all(
    search: str | None = Query(None, description="Filtra por título ou sinopse"),
    day: date | None = Query(None, description="Só as sessões deste dia, no fuso local"),
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=48),
    db: DbSession = Depends(get_db),
) -> SessionPage:
    items, total = SessionService(db).list_public(
        search=search, day=day, page=page, per_page=per_page
    )
    return SessionPage(
        items=[to_list_item(s) for s in items],
        total=total,
        page=page,
        total_pages=max(1, -(-total // per_page)),
    )


@publico.get("/{session_id}", response_model=SessionOut)
def detail(session_id: uuid.UUID, db: DbSession = Depends(get_db)) -> SessionOut:
    try:
        return to_session_out(SessionService(db).get_public(session_id))
    except SessionNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sessão não encontrada")


# --------------------------------------------------------------------------
# Gestao pelo organizador
# --------------------------------------------------------------------------

gestao = APIRouter(
    prefix="/organizer/sessions",
    tags=["Sessões (organizador)"],
    dependencies=[Depends(require_role(Role.ORGANIZER))],
)


def _as_http_error(error: Exception) -> HTTPException:
    """Converte a falha de negócio na resposta HTTP correspondente."""
    if isinstance(error, RoomNotFound):
        return HTTPException(status.HTTP_404_NOT_FOUND, "Sala não encontrada")
    if isinstance(error, MovieNotFound):
        return HTTPException(status.HTTP_404_NOT_FOUND, "Filme não encontrado no catálogo")
    if isinstance(error, SessionNotFound):
        return HTTPException(status.HTTP_404_NOT_FOUND, "Sessão não encontrada")
    if isinstance(error, RoomBusy):
        return HTTPException(
            status.HTTP_409_CONFLICT,
            "A sala está ocupada nesse intervalo. Uma sessão reserva a sala pelo tempo do "
            "filme mais a limpeza, então o horário precisa cair depois que a anterior libera.",
        )
    if isinstance(error, SessionInThePast):
        return HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "A sessão precisa começar no futuro"
        )
    if isinstance(error, SessionAlreadyCancelled):
        return HTTPException(status.HTTP_409_CONFLICT, "Esta sessão foi cancelada")
    if isinstance(error, SessionHasTickets):
        return HTTPException(
            status.HTTP_409_CONFLICT,
            "Esta sessão já vendeu ingressos. Para tirá-la do cartaz, cancele — "
            "assim quem comprou continua vendo o que aconteceu.",
        )
    if isinstance(error, SessionSold):
        return HTTPException(
            status.HTTP_409_CONFLICT,
            f"Esta sessão já vendeu {error.sold} ingresso(s) e não pode ser cancelada. "
            "Para tirá-la do cartaz sem prejudicar quem comprou, despublique. "
            "Se ela realmente não vai acontecer, cancele antes os pedidos.",
        )
    if isinstance(error, SessionIsPublished):
        return HTTPException(
            status.HTTP_409_CONFLICT,
            "Sessão publicada não é excluída. Despublique para tirá-la do cartaz, "
            "ou cancele se já houver interessados.",
        )
    if isinstance(error, PricesDoNotCoverSectors):
        return HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Falta definir preço para: {', '.join(error.missing)}",
        )
    raise error


@gestao.get("", response_model=list[SessionOut])
def mine(
    user: User = Depends(require_role(Role.ORGANIZER)),
    db: DbSession = Depends(get_db),
) -> list[SessionOut]:
    servico = SessionService(db)
    sessions = servico.list_for_organizer(user.id)

    # As contagens acompanham cada sessão: dizem o estrago antes de cancelar e
    # se a sessão pode ser apagada. Uma consulta para a lista toda.
    contagens = servico.ticket_counts([s.id for s in sessions])
    return [
        to_session_out(
            s,
            sold=contagens.get(s.id, (0, 0))[0],
            teve_ingressos=contagens.get(s.id, (0, 0))[1] > 0,
        )
        for s in sessions
    ]


@gestao.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create(
    data: SessionCreate,
    user: User = Depends(require_role(Role.ORGANIZER)),
    db: DbSession = Depends(get_db),
) -> SessionOut:
    try:
        return to_session_out(SessionService(db).create(user.id, data))
    except Exception as e:
        raise _as_http_error(e)


@gestao.post("/batch", response_model=BatchResult, status_code=status.HTTP_201_CREATED)
def create_batch(
    data: SessionRepeat,
    user: User = Depends(require_role(Role.ORGANIZER)),
    db: DbSession = Depends(get_db),
) -> BatchResult:
    """Cria a mesma sessão em vários dias, no mesmo horário.

    Dia com a sala ocupada é pulado e volta em `skipped`, com o motivo — o
    lote não é abortado por causa de um dia. Declarado antes de
    `/{session_id}` porque o roteador casa na ordem.
    """
    try:
        resultado = SessionService(db).create_batch(user.id, data)
    except Exception as e:
        raise _as_http_error(e)

    return BatchResult(
        created=[to_session_out(s) for s in resultado["created"]],
        skipped=[SkippedDate(**p) for p in resultado["skipped"]],
    )


@gestao.get("/{session_id}", response_model=SessionOut)
def detail_own(
    session_id: uuid.UUID,
    user: User = Depends(require_role(Role.ORGANIZER)),
    db: DbSession = Depends(get_db),
) -> SessionOut:
    try:
        return to_session_out(SessionService(db).get_for_organizer(session_id, user.id))
    except Exception as e:
        raise _as_http_error(e)


@gestao.patch("/{session_id}", response_model=SessionOut)
def update(
    session_id: uuid.UUID,
    data: SessionUpdate,
    user: User = Depends(require_role(Role.ORGANIZER)),
    db: DbSession = Depends(get_db),
) -> SessionOut:
    try:
        return to_session_out(SessionService(db).update(session_id, user.id, data))
    except Exception as e:
        raise _as_http_error(e)


@gestao.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    session_id: uuid.UUID,
    user: User = Depends(require_role(Role.ORGANIZER)),
    db: DbSession = Depends(get_db),
) -> Response:
    """Apaga a sessão. Só rascunho, e só sem ingresso vendido."""
    try:
        SessionService(db).delete(session_id, user.id)
    except Exception as e:
        raise _as_http_error(e)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@gestao.post("/{session_id}/publish", response_model=SessionOut)
def publish(
    session_id: uuid.UUID,
    user: User = Depends(require_role(Role.ORGANIZER)),
    db: DbSession = Depends(get_db),
) -> SessionOut:
    try:
        return to_session_out(SessionService(db).publish(session_id, user.id))
    except Exception as e:
        raise _as_http_error(e)


@gestao.post("/{session_id}/unpublish", response_model=SessionOut)
def unpublish(
    session_id: uuid.UUID,
    user: User = Depends(require_role(Role.ORGANIZER)),
    db: DbSession = Depends(get_db),
) -> SessionOut:
    try:
        return to_session_out(SessionService(db).unpublish(session_id, user.id))
    except Exception as e:
        raise _as_http_error(e)


@gestao.post("/{session_id}/cancel", response_model=SessionOut)
def cancel(
    session_id: uuid.UUID,
    user: User = Depends(require_role(Role.ORGANIZER)),
    db: DbSession = Depends(get_db),
) -> SessionOut:
    try:
        return to_session_out(SessionService(db).cancel(session_id, user.id))
    except Exception as e:
        raise _as_http_error(e)


@gestao.post("/{session_id}/cancel-orders", response_model=OrdersCancelled)
def cancel_orders(
    session_id: uuid.UUID,
    user: User = Depends(require_role(Role.ORGANIZER)),
    db: DbSession = Depends(get_db),
) -> OrdersCancelled:
    """Cancela todos os pedidos da sessão, despublicando-a antes.

    Passo separado do cancelamento da sessão: é ele que desfaz compras de
    pessoas reais, e precisa ser pedido explicitamente. Ver decisão D30.
    """
    servico = SessionService(db)
    try:
        quantos = servico.cancel_orders(session_id, user.id)
    except Exception as e:
        raise _as_http_error(e)

    session = servico.get_for_organizer(session_id, user.id)
    return OrdersCancelled(
        cancelled=quantos,
        session=to_session_out(session, sold=servico.occupied_seat_count(session_id)),
    )
