"""Sessões de cinema.

A vitrine é **pública**: quem ainda não tem conta consegue ver o que está em
cartaz, como em qualquer site de ingressos. A autenticação é exigida na hora
de reservar, não na hora de olhar. Ver decisão D10.

A gestão, essa sim, é do organizador.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session as DbSession

from app.core.deps import require_role
from app.db import get_db
from app.models.user import Role, User
from app.schemas.session import (
    SessionCreate,
    SessionOut,
    SessionPage,
    SessionUpdate,
    to_list_item,
    to_session_out,
)
from app.services.room_service import RoomNotFound
from app.services.session_service import (
    MovieNotFound,
    PricesDoNotCoverSectors,
    RoomBusy,
    SessionAlreadyCancelled,
    SessionInThePast,
    SessionNotFound,
    SessionService,
)

# --------------------------------------------------------------------------
# Vitrine publica
# --------------------------------------------------------------------------

publico = APIRouter(prefix="/sessions", tags=["Sessões (público)"])


@publico.get("", response_model=SessionPage)
def listar(
    busca: str | None = Query(None, description="Filtra por título ou sinopse"),
    page: int = Query(1, ge=1),
    por_pagina: int = Query(12, ge=1, le=48),
    db: DbSession = Depends(get_db),
) -> SessionPage:
    itens, total = SessionService(db).listar_publicas(
        busca=busca, page=page, por_pagina=por_pagina
    )
    return SessionPage(
        items=[to_list_item(s) for s in itens],
        total=total,
        page=page,
        total_pages=max(1, -(-total // por_pagina)),
    )


@publico.get("/{session_id}", response_model=SessionOut)
def detalhar(session_id: uuid.UUID, db: DbSession = Depends(get_db)) -> SessionOut:
    try:
        return to_session_out(SessionService(db).obter_publica(session_id))
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


def _traduz(erro: Exception) -> HTTPException:
    """Converte a falha de negócio na resposta HTTP correspondente."""
    if isinstance(erro, RoomNotFound):
        return HTTPException(status.HTTP_404_NOT_FOUND, "Sala não encontrada")
    if isinstance(erro, MovieNotFound):
        return HTTPException(status.HTTP_404_NOT_FOUND, "Filme não encontrado no catálogo")
    if isinstance(erro, SessionNotFound):
        return HTTPException(status.HTTP_404_NOT_FOUND, "Sessão não encontrada")
    if isinstance(erro, RoomBusy):
        return HTTPException(
            status.HTTP_409_CONFLICT, "Já existe uma sessão nessa sala nesse horário"
        )
    if isinstance(erro, SessionInThePast):
        return HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "A sessão precisa começar no futuro"
        )
    if isinstance(erro, SessionAlreadyCancelled):
        return HTTPException(status.HTTP_409_CONFLICT, "Esta sessão foi cancelada")
    if isinstance(erro, PricesDoNotCoverSectors):
        return HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Falta definir preço para: {', '.join(erro.faltando)}",
        )
    raise erro


@gestao.get("", response_model=list[SessionOut])
def minhas(
    user: User = Depends(require_role(Role.ORGANIZER)),
    db: DbSession = Depends(get_db),
) -> list[SessionOut]:
    return [to_session_out(s) for s in SessionService(db).listar_do_organizador(user.id)]


@gestao.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def criar(
    dados: SessionCreate,
    user: User = Depends(require_role(Role.ORGANIZER)),
    db: DbSession = Depends(get_db),
) -> SessionOut:
    try:
        return to_session_out(SessionService(db).criar(user.id, dados))
    except Exception as e:
        raise _traduz(e)


@gestao.get("/{session_id}", response_model=SessionOut)
def detalhar_minha(
    session_id: uuid.UUID,
    user: User = Depends(require_role(Role.ORGANIZER)),
    db: DbSession = Depends(get_db),
) -> SessionOut:
    try:
        return to_session_out(SessionService(db).obter_do_organizador(session_id, user.id))
    except Exception as e:
        raise _traduz(e)


@gestao.patch("/{session_id}", response_model=SessionOut)
def atualizar(
    session_id: uuid.UUID,
    dados: SessionUpdate,
    user: User = Depends(require_role(Role.ORGANIZER)),
    db: DbSession = Depends(get_db),
) -> SessionOut:
    try:
        return to_session_out(SessionService(db).atualizar(session_id, user.id, dados))
    except Exception as e:
        raise _traduz(e)


@gestao.post("/{session_id}/publish", response_model=SessionOut)
def publicar(
    session_id: uuid.UUID,
    user: User = Depends(require_role(Role.ORGANIZER)),
    db: DbSession = Depends(get_db),
) -> SessionOut:
    try:
        return to_session_out(SessionService(db).publicar(session_id, user.id))
    except Exception as e:
        raise _traduz(e)


@gestao.post("/{session_id}/unpublish", response_model=SessionOut)
def despublicar(
    session_id: uuid.UUID,
    user: User = Depends(require_role(Role.ORGANIZER)),
    db: DbSession = Depends(get_db),
) -> SessionOut:
    try:
        return to_session_out(SessionService(db).despublicar(session_id, user.id))
    except Exception as e:
        raise _traduz(e)


@gestao.post("/{session_id}/cancel", response_model=SessionOut)
def cancelar(
    session_id: uuid.UUID,
    user: User = Depends(require_role(Role.ORGANIZER)),
    db: DbSession = Depends(get_db),
) -> SessionOut:
    try:
        return to_session_out(SessionService(db).cancelar(session_id, user.id))
    except Exception as e:
        raise _traduz(e)
