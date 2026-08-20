"""Salas e seus setores.

A sala é cadastrada uma vez e reaproveitada por quantas sessões o organizador
quiser: redigitar o layout a cada sessão convidaria duas sessões da mesma sala
a divergirem por erro de digitação. Ver decisão D11.

O setor é geometria — onde ficam as poltronas VIP dentro da sala. O preço não
mora aqui: é decisão da sessão, porque a mesma sala tem preço de terça e preço
de sábado. Ver decisão D12.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

# Limites de sanidade. Uma sala real não tem 200 fileiras, e o mapa de assentos
# precisa caber numa tela.
MAX_FILEIRAS = 26  # A até Z
MAX_POLTRONAS_POR_FILEIRA = 40


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organizer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(80))
    location: Mapped[str | None] = mapped_column(String(160), default=None)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    sectors: Mapped[list["Sector"]] = relationship(
        back_populates="room",
        cascade="all, delete-orphan",
        order_by="Sector.display_order",
        lazy="selectin",
    )

    __table_args__ = (
        # Dois organizadores podem ter uma "Sala 1"; o mesmo organizador, não.
        UniqueConstraint("organizer_id", "name", name="uq_room_organizador_nome"),
    )

    @property
    def capacity(self) -> int:
        return sum(s.capacity for s in self.sectors)


class Sector(Base):
    __tablename__ = "sectors"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    room_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(60))
    rows: Mapped[int] = mapped_column(Integer)
    seats_per_row: Mapped[int] = mapped_column(Integer)
    # Ordem de exibição no mapa, da tela para o fundo da sala.
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    room: Mapped["Room"] = relationship(back_populates="sectors")

    __table_args__ = (
        UniqueConstraint("room_id", "name", name="uq_setor_sala_nome"),
        CheckConstraint(f"rows > 0 AND rows <= {MAX_FILEIRAS}", name="ck_setor_fileiras"),
        CheckConstraint(
            f"seats_per_row > 0 AND seats_per_row <= {MAX_POLTRONAS_POR_FILEIRA}",
            name="ck_setor_poltronas",
        ),
    )

    @property
    def capacity(self) -> int:
        return self.rows * self.seats_per_row

    @property
    def seat_codes(self) -> list[str]:
        """Códigos das poltronas do setor: A1, A2, ... B1, B2.

        Derivados da geometria em vez de gravados: pré-criar uma linha por
        poltrona encheria o banco de registros que só interessam quando
        alguém compra. Ver decisão D15.
        """
        return [
            f"{chr(ord('A') + fileira)}{numero}"
            for fileira in range(self.rows)
            for numero in range(1, self.seats_per_row + 1)
        ]
