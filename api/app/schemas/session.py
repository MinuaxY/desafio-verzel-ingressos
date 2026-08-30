"""Contratos de sessão.

Valores monetários trafegam em **centavos inteiros** (`price_cents`). O front
formata para exibir. Ver decisão D14.
"""
import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.session import AudioType, ScreenFormat, SessionStatus
from app.schemas.room import SectorOut

MAX_PRICE_CENTS = 100_000_00  # R$ 100.000, trava contra erro de digitação

# O mínimo é um centavo, e não zero. Sessão de graça parecia inofensiva, mas o
# pagamento simulado recusa valor zero — o cliente reservava a poltrona e não
# conseguia pagar nunca, ficando com um pedido morto. A tela de criação já
# exigia preço maior que zero; a API é que discordava dela. Ver decisão D33.
MIN_PRICE_CENTS = 1


class SectorPriceIn(BaseModel):
    sector_id: uuid.UUID
    price_cents: int = Field(ge=MIN_PRICE_CENTS, le=MAX_PRICE_CENTS)


class SessionCreate(BaseModel):
    catalog_id: str = Field(min_length=1, max_length=40, description="Id do filme no catálogo")
    room_id: uuid.UUID
    starts_at: datetime
    audio: AudioType = AudioType.SUBTITLED
    screen_format: ScreenFormat = ScreenFormat.TWO_D
    prices: list[SectorPriceIn] = Field(min_length=1)
    publish: bool = Field(False, description="Publica já; caso contrário nasce como rascunho")

    @field_validator("starts_at")
    @classmethod
    def require_timezone(cls, v: datetime) -> datetime:
        # Sem fuso não dá para saber que instante é esse. Recusar na entrada é
        # melhor que adivinhar e gravar errado.
        if v.tzinfo is None:
            raise ValueError("Informe o horário com fuso (ex.: 2026-09-12T21:00:00-03:00)")
        return v

    @field_validator("prices")
    @classmethod
    def one_price_per_sector(cls, v: list[SectorPriceIn]) -> list[SectorPriceIn]:
        ids = [p.sector_id for p in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Há mais de um preço para o mesmo setor")
        return v


class SessionRepeat(BaseModel):
    """Criação em lote: a mesma sessão em vários dias, no mesmo horário.

    As datas vêm escolhidas uma a uma, e não como regra do tipo "toda sexta
    até tal dia". Programação de cinema não é regular — um filme roda de
    quinta a domingo numa semana e só no fim de semana na seguinte —, e uma
    regra que não cobre isso obrigaria a apagar depois o que ela criou a mais.
    Ver decisão D27.
    """

    catalog_id: str = Field(min_length=1, max_length=40)
    room_id: uuid.UUID
    dates: list[date] = Field(min_length=1, max_length=60)
    time_of_day: time = Field(description="Horário local da sessão, ex.: 19:00")
    audio: AudioType = AudioType.SUBTITLED
    screen_format: ScreenFormat = ScreenFormat.TWO_D
    prices: list[SectorPriceIn] = Field(min_length=1)
    publish: bool = False

    @field_validator("prices")
    @classmethod
    def one_price_per_sector(cls, v: list[SectorPriceIn]) -> list[SectorPriceIn]:
        ids = [p.sector_id for p in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Há mais de um preço para o mesmo setor")
        return v


class SkippedDate(BaseModel):
    date: date
    reason: str


class SessionUpdate(BaseModel):
    starts_at: datetime | None = None
    prices: list[SectorPriceIn] | None = None
    audio: AudioType | None = None
    screen_format: ScreenFormat | None = None

    @field_validator("starts_at")
    @classmethod
    def require_timezone(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            raise ValueError("Informe o horário com fuso")
        return v


class SectorPriceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sector: SectorOut
    price_cents: int


class MovieOut(BaseModel):
    """Dados do filme como estavam quando a sessão foi criada. Ver decisão D13."""

    catalog_id: str
    title: str
    overview: str | None
    poster_url: str | None
    backdrop_url: str | None
    runtime_minutes: int | None
    year: int | None
    age_rating: str | None


class SessionOut(BaseModel):
    id: uuid.UUID
    movie: MovieOut
    room_id: uuid.UUID
    room_name: str
    room_location: str | None
    starts_at: datetime
    status: SessionStatus
    audio: AudioType
    screen_format: ScreenFormat
    capacity: int
    prices: list[SectorPriceOut]
    min_price_cents: int | None
    max_price_cents: int | None
    # Quantos ingressos desta sessão ocupam poltrona. Só é preenchido na visão
    # do organizador, que é quem precisa saber o estrago antes de cancelar.
    tickets_sold: int | None = None
    # Se a sessão já teve pedido algum dia, mesmo cancelado depois. É o que
    # decide se ela pode ser apagada de vez. Ver decisão D31.
    has_tickets: bool | None = None


class SessionListItem(BaseModel):
    """Versão enxuta para a vitrine: só o que o cartaz precisa mostrar."""

    id: uuid.UUID
    title: str
    poster_url: str | None
    year: int | None
    runtime_minutes: int | None
    age_rating: str | None
    audio: AudioType
    screen_format: ScreenFormat
    starts_at: datetime
    room_name: str
    room_location: str | None
    min_price_cents: int | None
    max_price_cents: int | None


class SessionPage(BaseModel):
    items: list[SessionListItem]
    total: int
    page: int
    total_pages: int


class BatchResult(BaseModel):
    """O que o lote criou, e o que ficou de fora com o motivo."""

    created: list[SessionOut]
    skipped: list[SkippedDate]


class OrdersCancelled(BaseModel):
    """Resultado do cancelamento em massa dos pedidos de uma sessão."""

    cancelled: int
    session: SessionOut


class DayInCartaz(BaseModel):
    """Um dia da barra de datas, com quantas sessões tem."""

    date: date
    total: int


# --------------------------------------------------------------------------
# Conversao dos models para os contratos de saida.
# Fica aqui, junto do contrato, para que o router nao precise conhecer a
# estrutura interna do model.
# --------------------------------------------------------------------------


def to_movie_out(session) -> MovieOut:
    return MovieOut(
        catalog_id=session.catalog_id,
        title=session.movie_title,
        overview=session.movie_overview,
        poster_url=session.movie_poster_url,
        backdrop_url=session.movie_backdrop_url,
        runtime_minutes=session.movie_runtime_minutes,
        year=session.movie_year,
        age_rating=session.movie_age_rating,
    )


def to_session_out(
    session, *, sold: int | None = None, teve_ingressos: bool | None = None
) -> SessionOut:
    faixa = session.price_range_cents
    return SessionOut(
        id=session.id,
        movie=to_movie_out(session),
        room_id=session.room_id,
        room_name=session.room.name,
        room_location=session.room.location,
        starts_at=session.starts_at,
        status=session.status,
        audio=session.audio,
        screen_format=session.screen_format,
        capacity=session.room.capacity,
        prices=[
            SectorPriceOut(sector=SectorOut.model_validate(p.sector), price_cents=p.price_cents)
            for p in sorted(session.prices, key=lambda p: p.sector.display_order)
        ],
        min_price_cents=faixa[0] if faixa else None,
        max_price_cents=faixa[1] if faixa else None,
        tickets_sold=sold,
        has_tickets=teve_ingressos,
    )


def to_list_item(session) -> SessionListItem:
    faixa = session.price_range_cents
    return SessionListItem(
        id=session.id,
        title=session.movie_title,
        poster_url=session.movie_poster_url,
        year=session.movie_year,
        runtime_minutes=session.movie_runtime_minutes,
        age_rating=session.movie_age_rating,
        audio=session.audio,
        screen_format=session.screen_format,
        starts_at=session.starts_at,
        room_name=session.room.name,
        room_location=session.room.location,
        min_price_cents=faixa[0] if faixa else None,
        max_price_cents=faixa[1] if faixa else None,
    )
