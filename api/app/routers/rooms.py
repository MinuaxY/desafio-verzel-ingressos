"""Salas do organizador."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.core.deps import require_role
from app.db import get_db
from app.models.user import Role, User
from app.schemas.room import RoomIn, RoomOut
from app.services.room_service import RoomNameAlreadyUsed, RoomNotFound, RoomService

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


@router.delete("/{room_id}", response_model=RoomOut)
def desativar(
    room_id: uuid.UUID,
    user: User = Depends(require_role(Role.ORGANIZER)),
    db: DbSession = Depends(get_db),
) -> RoomOut:
    """Desativa a sala. Não apaga: sessões passadas apontam para ela, e o
    histórico de quem comprou precisa continuar fazendo sentido."""
    try:
        return RoomOut.model_validate(RoomService(db).desativar(room_id, user.id))
    except RoomNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sala não encontrada")
