"""Sessões de cinema.

A sessão junta três coisas: qual filme (cópia dos dados do catálogo), onde e
quando (sala e horário) e por quanto (preço de cada setor).
"""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class AudioType(str, enum.Enum):
    """Como o filme é apresentado nesta sessão.

    Decisão do organizador, não do catálogo: o mesmo filme roda dublado às
    16h e legendado às 21h.
    """

    DUBBED = "DUBBED"        # Dublado
    SUBTITLED = "SUBTITLED"  # Legendado
    NATIONAL = "NATIONAL"    # Nacional — áudio original em português


class ScreenFormat(str, enum.Enum):
    TWO_D = "TWO_D"
    THREE_D = "THREE_D"


class SessionStatus(str, enum.Enum):
    """DRAFT não aparece para o público. PUBLISHED está à venda. CANCELLED foi
    cancelada depois de publicada e não volta atrás."""

    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    CANCELLED = "CANCELLED"


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organizer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    room_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rooms.id"), index=True)

    # --- Cópia dos dados do filme -----------------------------------------
    # Guardados na publicação, não consultados a cada exibição. Se o TMDb sair
    # do ar, mudar o título traduzido ou trocar o pôster, o ingresso que alguém
    # comprou precisa continuar mostrando o que foi vendido. Ingresso é
    # documento, não consulta ao vivo. Ver decisão D13.
    catalog_id: Mapped[str] = mapped_column(String(40), index=True)
    movie_title: Mapped[str] = mapped_column(String(255))
    movie_overview: Mapped[str | None] = mapped_column(Text, default=None)
    movie_poster_url: Mapped[str | None] = mapped_column(String(500), default=None)
    movie_backdrop_url: Mapped[str | None] = mapped_column(String(500), default=None)
    movie_runtime_minutes: Mapped[int | None] = mapped_column(Integer, default=None)
    movie_year: Mapped[int | None] = mapped_column(Integer, default=None)

    # Classificação indicativa ("L", "10", "12", "14", "16", "18"), copiada
    # junto com o resto na criação da sessão. Fica como texto e não como enum:
    # é dado de terceiro, e um valor inesperado deve aparecer na tela em vez de
    # derrubar a criação da sessão. None quando o filme não tem classificação
    # brasileira registrada.
    movie_age_rating: Mapped[str | None] = mapped_column(String(6), default=None)

    # --- Como esta sessão é exibida ---------------------------------------
    # Diferente do bloco acima, isto não vem do catálogo: é escolha de quem
    # publica. O mesmo filme tem sessão dublada e legendada no mesmo dia.
    audio: Mapped[AudioType] = mapped_column(
        SAEnum(AudioType, name="audio_type"), default=AudioType.SUBTITLED
    )
    screen_format: Mapped[ScreenFormat] = mapped_column(
        SAEnum(ScreenFormat, name="screen_format"), default=ScreenFormat.TWO_D
    )

    # --- Quando -----------------------------------------------------------
    # Sempre com fuso. Sessão de cinema é hora local, e gravar sem fuso obriga
    # a reescrever os dados existentes quando o erro aparece. Ver decisão D14.
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    status: Mapped[SessionStatus] = mapped_column(
        SAEnum(SessionStatus, name="session_status"), default=SessionStatus.DRAFT, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    room: Mapped["Room"] = relationship(lazy="selectin")  # noqa: F821
    prices: Mapped[list["SessionSectorPrice"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        # A mesma sala não pode ter duas sessões no mesmo instante — mas
        # cancelada não conta, porque ela não vai acontecer. Índice parcial e
        # não constraint, pela mesma razão do índice de poltrona: só o banco
        # decide o empate entre duas criações simultâneas, e uma constraint
        # cega deixaria o horário da cancelada preso para sempre.
        # Ver decisões D6 e D31.
        Index(
            "uq_sessao_sala_horario",
            "room_id",
            "starts_at",
            unique=True,
            postgresql_where=(status != SessionStatus.CANCELLED),
        ),
    )

    @property
    def is_public(self) -> bool:
        return self.status is SessionStatus.PUBLISHED

    @property
    def price_range_cents(self) -> tuple[int, int] | None:
        if not self.prices:
            return None
        valores = [p.price_cents for p in self.prices]
        return min(valores), max(valores)


class SessionSectorPrice(Base):
    """Preço de um setor numa sessão.

    O preço mora aqui, e não no setor, porque é decisão da sessão: a mesma sala
    tem preço de terça e preço de sábado. Ver decisão D12.

    Valor em centavos inteiros, nunca float: 0.1 + 0.2 não dá 0.3 em ponto
    flutuante, e esse erro aparece no centavo depois que já há ingresso
    emitido. Ver decisão D14.
    """

    __tablename__ = "session_sector_prices"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    sector_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sectors.id", ondelete="CASCADE"))
    price_cents: Mapped[int] = mapped_column(Integer)

    session: Mapped["Session"] = relationship(back_populates="prices")
    sector: Mapped["Sector"] = relationship(lazy="selectin")  # noqa: F821

    __table_args__ = (
        UniqueConstraint("session_id", "sector_id", name="uq_preco_sessao_setor"),
        CheckConstraint("price_cents >= 0", name="ck_preco_nao_negativo"),
    )
