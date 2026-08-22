"""Salas do organizador."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session as DbSession

from app.core.deps import require_role
from app.db import get_db
from app.models.user import Role, User
from app.schemas.room import RoomIn, RoomOut, RoomUpdate
from app.services.room_service import (
    RoomInUse,
    RoomLayoutLocked,
    RoomNameAlreadyUsed,
    RoomNotFound,
    RoomService,
    RoomTooTall,
    SeatOutsideSector,
)

router = APIRouter(
    prefix="/rooms",
    tags=["Salas"],
    dependencies=[Depends(require_role(Role.ORGANIZER))],
)


@router.get("", response_model=list[RoomOut])
def listar(
    user: User = Depends(require_role(Role.ORGANIZER)),
    db: DbSession = Depends(get_db),
) -> list[RoomOut]:
    return [RoomOut.model_validate(r) for r in RoomService(db).listar(user.id)]


@router.post("", response_model=RoomOut, status_code=status.HTTP_201_CREATED)
def criar(
    dados: RoomIn,
    user: User = Depends(require_role(Role.ORGANIZER)),
    db: DbSession = Depends(get_db),
) -> RoomOut:
    try:
        return RoomOut.model_validate(RoomService(db).criar(user.id, dados))
    except RoomNameAlreadyUsed:
        raise HTTPException(status.HTTP_409_CONFLICT, "Você já tem uma sala com esse nome")
    except RoomTooTall as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"A sala tem {e.total} fileiras somando todos os setores, e o limite é 26 "
            "— as fileiras são nomeadas por letra.",
        )
    except SeatOutsideSector as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"O setor {e.setor} não tem estas poltronas: {', '.join(e.codigos)}",
        )


@router.get("/{room_id}", response_model=RoomOut)
def detalhar(
    room_id: uuid.UUID,
    user: User = Depends(require_role(Role.ORGANIZER)),
    db: DbSession = Depends(get_db),
) -> RoomOut:
    try:
        return RoomOut.model_validate(RoomService(db).obter_do_organizador(room_id, user.id))
    except RoomNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sala não encontrada")


@router.patch("/{room_id}", response_model=RoomOut)
def atualizar(
    room_id: uuid.UUID,
    dados: RoomUpdate,
    user: User = Depends(require_role(Role.ORGANIZER)),
    db: DbSession = Depends(get_db),
) -> RoomOut:
    """Altera a sala. Nome e endereço sempre; geometria só enquanto a sala não
    tiver nenhuma sessão."""
    try:
        return RoomOut.model_validate(RoomService(db).atualizar(room_id, user.id, dados))
    except RoomNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sala não encontrada")
    except RoomNameAlreadyUsed:
        raise HTTPException(status.HTTP_409_CONFLICT, "Você já tem uma sala com esse nome")
    except RoomLayoutLocked:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Esta sala já foi usada em sessões, então o layout de poltronas não pode mais "
            "mudar — ingressos vendidos apontam para lugares específicos. Nome e endereço "
            "continuam editáveis.",
        )
    except RoomTooTall as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"A sala tem {e.total} fileiras somando todos os setores, e o limite é 26.",
        )
    except SeatOutsideSector as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"O setor {e.setor} não tem estas poltronas: {', '.join(e.codigos)}",
        )


@router.delete("/{room_id}")
def remover(
    room_id: uuid.UUID,
    user: User = Depends(require_role(Role.ORGANIZER)),
    db: DbSession = Depends(get_db),
):
    """Remove a sala.

    Apaga de vez se ela nunca teve sessão; desativa se já teve, porque sessão
    passada aponta para ela. Sala com sessão futura não é removida.
    """
    try:
        sala = RoomService(db).remover(room_id, user.id)
    except RoomNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sala não encontrada")
    except RoomInUse as e:
        plural = "sessões futuras" if e.sessoes > 1 else "sessão futura"
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Esta sala tem {e.sessoes} {plural}. Cancele ou despublique antes de removê-la.",
        )

    if sala is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return RoomOut.model_validate(sala)
