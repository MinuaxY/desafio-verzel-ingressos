"""Salas e seus setores.

A sala é cadastrada uma vez e reaproveitada por quantas sessões o organizador
quiser: redigitar o layout a cada sessão convidaria duas sessões da mesma sala
a divergirem por erro de digitação. Ver decisão D11.

O setor é geometria — onde ficam as poltronas VIP dentro da sala. O preço não
mora aqui: é decisão da sessão, porque a mesma sala tem preço de terça e preço
de sábado. Ver decisão D12.
"""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class SeatKind(str, enum.Enum):
    """Natureza de uma poltrona.

    Salas de espetáculo no Brasil precisam oferecer lugares acessíveis (Lei
    10.098 e NBR 9050). Isso é característica da poltrona, e não enfeite de
    interface: se a marcação vivesse só no front, o sistema não teria registro
    de que aquele lugar é reservado a quem precisa dele.

    A poltrona comum não vira registro — ausência já significa STANDARD.

    O sistema **não valida elegibilidade**: não há como conferir laudo por aqui,
    e cinemas reais checam na entrada. Ver decisão D16.
    """

    WHEELCHAIR = "WHEELCHAIR"              # espaço para cadeira de rodas
    COMPANION = "COMPANION"                # acompanhante, ao lado do espaço
    OBESE = "OBESE"                        # assento largo
    REDUCED_MOBILITY = "REDUCED_MOBILITY"  # mobilidade reduzida, junto ao corredor

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
    special_seats: Mapped[list["SeatAttribute"]] = relationship(
        back_populates="sector",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

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

    def has_seat(self, seat_code: str) -> bool:
        """A poltrona existe na geometria deste setor?

        Impede marcar como acessível uma poltrona que não existe — G1 num setor
        que só vai até a fileira F.
        """
        codigo = seat_code.strip().upper()
        if len(codigo) < 2 or not codigo[1:].isdigit():
            return False
        fileira = ord(codigo[0]) - ord("A")
        numero = int(codigo[1:])
        return 0 <= fileira < self.rows and 1 <= numero <= self.seats_per_row


class SeatAttribute(Base):
    """Poltrona com característica especial dentro de um setor.

    Só existe registro para poltrona que foge do comum: uma sala de 88 lugares
    com seis assentos acessíveis guarda seis linhas, não 88.
    """

    __tablename__ = "seat_attributes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    sector_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sectors.id", ondelete="CASCADE"), index=True
    )
    seat_code: Mapped[str] = mapped_column(String(4))
    kind: Mapped[SeatKind] = mapped_column(SAEnum(SeatKind, name="seat_kind"))

    sector: Mapped["Sector"] = relationship(back_populates="special_seats")

    __table_args__ = (
        UniqueConstraint("sector_id", "seat_code", name="uq_assento_setor_codigo"),
    )
