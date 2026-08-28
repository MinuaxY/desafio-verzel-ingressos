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
    ForeignKeyConstraint,
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
        # Alvo da chave composta de session_sector_prices. Redundante com a
        # chave primária, e exigida pelo Postgres: uma chave estrangeira só
        # aponta para colunas com unicidade declarada. Ver decisão D35.
        UniqueConstraint("id", "room_id", name="uq_session_id_room"),
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
    session_id: Mapped[uuid.UUID] = mapped_column(index=True)
    sector_id: Mapped[uuid.UUID] = mapped_column()

    # Derivável da sessão, e guardada mesmo assim: é a coluna que as duas
    # chaves compostas abaixo compartilham, e é o compartilhamento que prova a
    # regra. Ver decisão D35.
    room_id: Mapped[uuid.UUID] = mapped_column()

    price_cents: Mapped[int] = mapped_column(Integer)

    # As duas chaves são compostas e dividem `room_id`, então a sessão e o
    # setor precisam ser da mesma sala para a linha existir. Sem `primaryjoin`
    # explícito o SQLAlchemy não saberia qual das duas usar em cada lado.
    session: Mapped["Session"] = relationship(
        back_populates="prices",
        primaryjoin="SessionSectorPrice.session_id == Session.id",
        foreign_keys="SessionSectorPrice.session_id",
    )
    sector: Mapped["Sector"] = relationship(  # noqa: F821
        lazy="selectin",
        primaryjoin="SessionSectorPrice.sector_id == Sector.id",
        foreign_keys="SessionSectorPrice.sector_id",
    )

    __table_args__ = (
        # O preço aponta para um setor **da sala daquela sessão**, e quem
        # garante isso é o banco.
        #
        # Antes, `session_id` e `sector_id` referenciavam suas tabelas de forma
        # independente: nada impedia gravar o preço de um setor de outra sala.
        # Só o serviço conferia, e invariante que vive apenas no serviço é
        # invariante que a próxima rota esquece.
        #
        # A prova está no `room_id` compartilhado: a primeira chave exige que a
        # sessão esteja nessa sala, a segunda exige o mesmo do setor. Sendo a
        # mesma coluna, as duas falam da mesma sala. Ver decisão D35.
        ForeignKeyConstraint(
            ["session_id", "room_id"],
            ["sessions.id", "sessions.room_id"],
            name="fk_session_price_session_room",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["sector_id", "room_id"],
            ["sectors.id", "sectors.room_id"],
            name="fk_session_price_sector_room",
            ondelete="CASCADE",
        ),
        UniqueConstraint("session_id", "sector_id", name="uq_session_price_sector"),
        # Mínimo de um centavo, alinhado com o contrato da API. O banco aceitava
        # zero enquanto a aplicação já recusava — e sessão de graça deixa o
        # cliente com um pedido que nunca pode ser pago. Ver decisões D33 e D35.
        CheckConstraint("price_cents >= 1", name="ck_session_price_positive"),
    )
