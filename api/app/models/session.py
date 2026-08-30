"""Sessões de cinema.

A sessão junta três coisas: qual filme (cópia dos dados do catálogo), onde e
quando (sala e horário) e por quanto (preço de cada setor).
"""
import enum
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import (
    CheckConstraint,
    func,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
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


# Duração presumida quando o catálogo não informa a do filme. Precisa existir
# porque a sala é reservada pelo tempo que a sessão ocupa, e um valor ausente
# viraria ocupação zero — a sala pareceria livre no minuto seguinte.
DEFAULT_RUNTIME_MINUTES = 120

# Folga entre uma sessão e a seguinte na mesma sala: o público sai, a equipe
# limpa, a próxima entra. Sem ela, duas sessões coladas passariam pela trava e
# a sala teria plateia entrando enquanto a outra ainda sai.
TURNAROUND_MINUTES = 20


def occupation_end(starts_at: datetime, runtime_minutes: int | None) -> datetime:
    """Até quando a sala fica indisponível por causa desta sessão.

    Não é o fim do filme: inclui a folga de limpeza. O nome da coluna diz isso
    — `occupies_until`, e não `ends_at`. Ver decisão D37.
    """
    minutos = (runtime_minutes or DEFAULT_RUNTIME_MINUTES) + TURNAROUND_MINUTES
    return starts_at + timedelta(minutes=minutos)


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

    # Até quando a sala fica ocupada: início + duração do filme + folga de
    # limpeza. Materializada, e não calculada na hora, porque a trava de
    # sobreposição é um índice — e índice do Postgres só aceita expressão
    # imutável. `timestamptz + interval` é apenas estável, então a soma precisa
    # estar gravada. Ver decisão D37.
    occupies_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))

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
        # Alvo da chave composta de session_sector_prices. Redundante com a
        # chave primária, e exigida pelo Postgres: uma chave estrangeira só
        # aponta para colunas com unicidade declarada. Ver decisão D35.
        UniqueConstraint("id", "room_id", name="uq_session_id_room"),
        # Duas sessões não podem **se sobrepor** na mesma sala.
        #
        # Antes a trava comparava só igualdade de horário, então duas sessões
        # de duas horas às 20:00 e às 20:01 não colidiam — a sala ficava com
        # duas plateias. A pergunta certa não é "começam no mesmo instante",
        # é "ocupam a sala ao mesmo tempo".
        #
        # Cancelada continua de fora, pela mesma razão da D31: ela não vai
        # acontecer, então não ocupa nada. Ver decisões D6, D31 e D37.
        ExcludeConstraint(
            ("room_id", "="),
            (func.tstzrange(starts_at, occupies_until), "&&"),
            name="ex_session_room_overlap",
            using="gist",
            where=(status != SessionStatus.CANCELLED),
        ),
        # Ocupação vazia passaria pela trava acima sem sobrepor nada.
        CheckConstraint("occupies_until > starts_at", name="ck_session_occupation"),
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
