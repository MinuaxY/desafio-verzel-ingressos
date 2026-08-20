"""Acesso a dados de sala. Sem regra de negócio."""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.models.room import Room, SeatAttribute, Sector


class RoomRepository:
    def __init__(self, db: DbSession) -> None:
        self.db = db

    def list_by_organizer(self, organizer_id: uuid.UUID, *, apenas_ativas: bool = True) -> list[Room]:
        consulta = select(Room).where(Room.organizer_id == organizer_id)
        if apenas_ativas:
            consulta = consulta.where(Room.active.is_(True))
        return list(self.db.scalars(consulta.order_by(Room.name)))

    def get(self, room_id: uuid.UUID) -> Room | None:
        return self.db.get(Room, room_id)

    def get_by_name(self, organizer_id: uuid.UUID, name: str) -> Room | None:
        return self.db.scalar(
            select(Room).where(Room.organizer_id == organizer_id, Room.name == name)
        )

    def create(
        self,
        *,
        organizer_id: uuid.UUID,
        name: str,
        location: str | None,
        sectors: list[dict],
    ) -> Room:
        room = Room(organizer_id=organizer_id, name=name, location=location)
        room.sectors = [
            Sector(
                **{k: v for k, v in dados.items() if k != "special_seats"},
                special_seats=[SeatAttribute(**a) for a in dados.get("special_seats", [])],
            )
            for dados in sectors
        ]
        self.db.add(room)
        self.db.commit()
        self.db.refresh(room)
        return room

    def deactivate(self, room: Room) -> Room:
        room.active = False
        self.db.commit()
        self.db.refresh(room)
        return room
