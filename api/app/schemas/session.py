"""Contratos de sessão.

Valores monetários trafegam em **centavos inteiros** (`price_cents`). O front
formata para exibir. Ver decisão D14.
"""
import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.session import AudioType, ScreenFormat, SessionStatus
from app.schemas.room import SectorOut

PRECO_MAXIMO_CENTAVOS = 100_000_00  # R$ 100.000, trava contra erro de digitação


class SectorPriceIn(BaseModel):
    sector_id: uuid.UUID
    price_cents: int = Field(ge=0, le=PRECO_MAXIMO_CENTAVOS)


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
    def exige_fuso(cls, v: datetime) -> datetime:
        # Sem fuso não dá para saber que instante é esse. Recusar na entrada é
        # melhor que adivinhar e gravar errado.
        if v.tzinfo is None:
            raise ValueError("Informe o horário com fuso (ex.: 2026-09-12T21:00:00-03:00)")
        return v

    @field_validator("prices")
    @classmethod
    def um_preco_por_setor(cls, v: list[SectorPriceIn]) -> list[SectorPriceIn]:
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
    def um_preco_por_setor(cls, v: list[SectorPriceIn]) -> list[SectorPriceIn]:
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
    def exige_fuso(cls, v: datetime | None) -> datetime | None:
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


class DayInCartaz(BaseModel):
    """Um dia da barra de datas, com quantas sessões tem."""

    date: date
    total: int


# --------------------------------------------------------------------------
# Conversao dos models para os contratos de saida.
# Fica aqui, junto do contrato, para que o router nao precise conhecer a
# estrutura interna do model.
# --------------------------------------------------------------------------


def to_movie_out(sessao) -> MovieOut:
    return MovieOut(
        catalog_id=sessao.catalog_id,
        title=sessao.movie_title,
        overview=sessao.movie_overview,
        poster_url=sessao.movie_poster_url,
        backdrop_url=sessao.movie_backdrop_url,
        runtime_minutes=sessao.movie_runtime_minutes,
        year=sessao.movie_year,
        age_rating=sessao.movie_age_rating,
    )


def to_session_out(sessao) -> SessionOut:
    faixa = sessao.price_range_cents
    return SessionOut(
        id=sessao.id,
        movie=to_movie_out(sessao),
        room_id=sessao.room_id,
        room_name=sessao.room.name,
        room_location=sessao.room.location,
        starts_at=sessao.starts_at,
        status=sessao.status,
        audio=sessao.audio,
        screen_format=sessao.screen_format,
        capacity=sessao.room.capacity,
        prices=[
            SectorPriceOut(sector=SectorOut.model_validate(p.sector), price_cents=p.price_cents)
            for p in sorted(sessao.prices, key=lambda p: p.sector.display_order)
        ],
        min_price_cents=faixa[0] if faixa else None,
        max_price_cents=faixa[1] if faixa else None,
    )


def to_list_item(sessao) -> SessionListItem:
    faixa = sessao.price_range_cents
    return SessionListItem(
        id=sessao.id,
        title=sessao.movie_title,
        poster_url=sessao.movie_poster_url,
        year=sessao.movie_year,
        runtime_minutes=sessao.movie_runtime_minutes,
        age_rating=sessao.movie_age_rating,
        audio=sessao.audio,
        screen_format=sessao.screen_format,
        starts_at=sessao.starts_at,
        room_name=sessao.room.name,
        room_location=sessao.room.location,
        min_price_cents=faixa[0] if faixa else None,
        max_price_cents=faixa[1] if faixa else None,
    )
