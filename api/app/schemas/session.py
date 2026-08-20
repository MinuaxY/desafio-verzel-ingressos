"""Contratos de sessão.

Valores monetários trafegam em **centavos inteiros** (`price_cents`). O front
formata para exibir. Ver decisão D14.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.session import SessionStatus
from app.schemas.room import SectorOut

PRECO_MAXIMO_CENTAVOS = 100_000_00  # R$ 100.000, trava contra erro de digitação


class SectorPriceIn(BaseModel):
    sector_id: uuid.UUID
    price_cents: int = Field(ge=0, le=PRECO_MAXIMO_CENTAVOS)


class SessionCreate(BaseModel):
    catalog_id: str = Field(min_length=1, max_length=40, description="Id do filme no catálogo")
    room_id: uuid.UUID
    starts_at: datetime
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


class SessionUpdate(BaseModel):
    starts_at: datetime | None = None
    prices: list[SectorPriceIn] | None = None

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


class SessionOut(BaseModel):
    id: uuid.UUID
    movie: MovieOut
    room_id: uuid.UUID
    room_name: str
    room_location: str | None
    starts_at: datetime
    status: SessionStatus
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
        starts_at=sessao.starts_at,
        room_name=sessao.room.name,
        room_location=sessao.room.location,
        min_price_cents=faixa[0] if faixa else None,
        max_price_cents=faixa[1] if faixa else None,
    )
