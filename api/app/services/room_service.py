"""Regra de negócio das salas."""
import uuid

from sqlalchemy.orm import Session as DbSession

from app.models.room import Room
from app.repositories.room_repository import RoomRepository
from app.schemas.room import RoomIn


class RoomNameAlreadyUsed(Exception):
    pass


class RoomNotFound(Exception):
    pass


class RoomNotOwned(Exception):
    pass


class RoomService:
    def __init__(self, db: DbSession) -> None:
        self.rooms = RoomRepository(db)

    def listar(self, organizer_id: uuid.UUID) -> list[Room]:
        return self.rooms.list_by_organizer(organizer_id)

    def criar(self, organizer_id: uuid.UUID, dados: RoomIn) -> Room:
        if self.rooms.get_by_name(organizer_id, dados.name):
            raise RoomNameAlreadyUsed
        return self.rooms.create(
            organizer_id=organizer_id,
            name=dados.name,
            location=dados.location,
            sectors=[s.model_dump() for s in dados.sectors],
        )

    def obter_do_organizador(self, room_id: uuid.UUID, organizer_id: uuid.UUID) -> Room:
        """Sala inexistente e sala de outro organizador são erros distintos.

        Quem não é dono recebe 'não encontrada', e não 'não é sua': confirmar a
        existência entregaria a quem sonda quais salas existem no sistema.
        """
        room = self.rooms.get(room_id)
        if room is None or room.organizer_id != organizer_id:
            raise RoomNotFound
        return room

    def desativar(self, room_id: uuid.UUID, organizer_id: uuid.UUID) -> Room:
        # Desativa em vez de apagar: sessões passadas apontam para a sala, e o
        # histórico de quem comprou precisa continuar fazendo sentido.
        return self.rooms.deactivate(self.obter_do_organizador(room_id, organizer_id))
