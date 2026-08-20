"""Contratos de sala e setor."""
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.room import MAX_FILEIRAS, MAX_POLTRONAS_POR_FILEIRA


class SectorIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    rows: int = Field(ge=1, le=MAX_FILEIRAS, description="Quantidade de fileiras (A, B, C…)")
    seats_per_row: int = Field(ge=1, le=MAX_POLTRONAS_POR_FILEIRA)
    display_order: int = Field(0, ge=0, description="Ordem no mapa, da tela para o fundo")

    @field_validator("name")
    @classmethod
    def limpa_nome(cls, v: str) -> str:
        return v.strip()


class SectorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    rows: int
    seats_per_row: int
    display_order: int
    capacity: int


class RoomIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    location: str | None = Field(None, max_length=160)
    sectors: list[SectorIn] = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def limpa_nome(cls, v: str) -> str:
        return v.strip()

    @field_validator("sectors")
    @classmethod
    def nomes_de_setor_unicos(cls, v: list[SectorIn]) -> list[SectorIn]:
        nomes = [s.name.casefold() for s in v]
        if len(nomes) != len(set(nomes)):
            raise ValueError("Os setores da sala precisam ter nomes diferentes")
        return v


class RoomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    location: str | None
    active: bool
    capacity: int
    sectors: list[SectorOut]
