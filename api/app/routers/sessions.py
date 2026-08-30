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
def dias_em_cartaz(
    dias: int = Query(14, ge=1, le=60, description="Quantos dias olhar para a frente"),
    busca: str | None = Query(None),
    db: DbSession = Depends(get_db),
) -> list[DayInCartaz]:
    """Dias que têm sessão, para a barra de datas da vitrine.

    Declarado antes de `/{session_id}` de propósito: o roteador casa na ordem,
    e "days" seria capturado como se fosse um id.
    """
    contagem = SessionService(db).dias_em_cartaz(dias=dias, busca=busca)
    return [DayInCartaz(date=d, total=t) for d, t in sorted(contagem.items())]


@publico.get("", response_model=SessionPage)
def listar(
    busca: str | None = Query(None, description="Filtra por título ou sinopse"),
    dia: date | None = Query(None, description="Só as sessões deste dia, no fuso local"),
    page: int = Query(1, ge=1),
    por_pagina: int = Query(12, ge=1, le=48),
    db: DbSession = Depends(get_db),
) -> SessionPage:
    itens, total = SessionService(db).listar_publicas(
        busca=busca, dia=dia, page=page, por_pagina=por_pagina
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
            status.HTTP_409_CONFLICT,
            "A sala está ocupada nesse intervalo. Uma sessão reserva a sala pelo tempo do "
            "filme mais a limpeza, então o horário precisa cair depois que a anterior libera.",
        )
    if isinstance(erro, SessionInThePast):
        return HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "A sessão precisa começar no futuro"
        )
    if isinstance(erro, SessionAlreadyCancelled):
        return HTTPException(status.HTTP_409_CONFLICT, "Esta sessão foi cancelada")
    if isinstance(erro, SessionHasTickets):
        return HTTPException(
            status.HTTP_409_CONFLICT,
            "Esta sessão já vendeu ingressos. Para tirá-la do cartaz, cancele — "
            "assim quem comprou continua vendo o que aconteceu.",
        )
    if isinstance(erro, SessionSold):
        return HTTPException(
            status.HTTP_409_CONFLICT,
            f"Esta sessão já vendeu {erro.vendidos} ingresso(s) e não pode ser cancelada. "
            "Para tirá-la do cartaz sem prejudicar quem comprou, despublique. "
            "Se ela realmente não vai acontecer, cancele antes os pedidos.",
        )
    if isinstance(erro, SessionIsPublished):
        return HTTPException(
            status.HTTP_409_CONFLICT,
            "Sessão publicada não é excluída. Despublique para tirá-la do cartaz, "
            "ou cancele se já houver interessados.",
        )
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
    servico = SessionService(db)
    sessoes = servico.listar_do_organizador(user.id)

    # As contagens acompanham cada sessão: dizem o estrago antes de cancelar e
    # se a sessão pode ser apagada. Uma consulta para a lista toda.
    contagens = servico.contagens_de_ingressos([s.id for s in sessoes])
    return [
        to_session_out(
            s,
            vendidos=contagens.get(s.id, (0, 0))[0],
            teve_ingressos=contagens.get(s.id, (0, 0))[1] > 0,
        )
        for s in sessoes
    ]


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


@gestao.post("/batch", response_model=BatchResult, status_code=status.HTTP_201_CREATED)
def criar_em_lote(
    dados: SessionRepeat,
    user: User = Depends(require_role(Role.ORGANIZER)),
    db: DbSession = Depends(get_db),
) -> BatchResult:
    """Cria a mesma sessão em vários dias, no mesmo horário.

    Dia com a sala ocupada é pulado e volta em `skipped`, com o motivo — o
    lote não é abortado por causa de um dia. Declarado antes de
    `/{session_id}` porque o roteador casa na ordem.
    """
    try:
        resultado = SessionService(db).criar_em_lote(user.id, dados)
    except Exception as e:
        raise _traduz(e)

    return BatchResult(
        created=[to_session_out(s) for s in resultado["created"]],
        skipped=[SkippedDate(**p) for p in resultado["skipped"]],
    )


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


@gestao.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(
    session_id: uuid.UUID,
    user: User = Depends(require_role(Role.ORGANIZER)),
    db: DbSession = Depends(get_db),
) -> Response:
    """Apaga a sessão. Só rascunho, e só sem ingresso vendido."""
    try:
        SessionService(db).excluir(session_id, user.id)
    except Exception as e:
        raise _traduz(e)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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


@gestao.post("/{session_id}/cancel-orders", response_model=OrdersCancelled)
def cancelar_pedidos(
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
        quantos = servico.cancelar_pedidos(session_id, user.id)
    except Exception as e:
        raise _traduz(e)

    sessao = servico.obter_do_organizador(session_id, user.id)
    return OrdersCancelled(
        cancelled=quantos,
        session=to_session_out(sessao, vendidos=servico.ingressos_vendidos(session_id)),
    )
