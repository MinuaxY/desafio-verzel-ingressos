"""Contratos de sala e setor."""
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.room import MAX_ROWS, MAX_SEATS_PER_ROW, SeatKind


class SpecialSeatIn(BaseModel):
    seat_code: str = Field(min_length=2, max_length=4, description="Ex.: A1, F12")
    kind: SeatKind

    @field_validator("seat_code")
    @classmethod
    def normalize(cls, v: str) -> str:
        return v.strip().upper()


class SpecialSeatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    seat_code: str
    kind: SeatKind


class SectorIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    rows: int = Field(ge=1, le=MAX_ROWS, description="Quantidade de fileiras (A, B, C…)")
    seats_per_row: int = Field(ge=1, le=MAX_SEATS_PER_ROW)
    display_order: int = Field(0, ge=0, description="Ordem no mapa, da tela para o fundo")
    special_seats: list[SpecialSeatIn] = Field(
        default_factory=list,
        description="Poltronas acessiveis. Ausencia significa poltrona comum.",
    )
    aisles: list[int] = Field(
        default_factory=list,
        description="Corredores: posicoes depois das quais ha passagem. Ex.: [3, 9]",
    )

    @field_validator("name")
    @classmethod
    def limpa_nome(cls, v: str) -> str:
        return v.strip()

    @field_validator("special_seats")
    @classmethod
    def sem_poltrona_repetida(cls, v: list[SpecialSeatIn]) -> list[SpecialSeatIn]:
        codigos = [s.seat_code for s in v]
        if len(codigos) != len(set(codigos)):
            raise ValueError("A mesma poltrona foi marcada mais de uma vez")
        return v

    @model_validator(mode="after")
    def corredores_dentro_da_fileira(self) -> "SectorIn":
        """Corredor na posicao 0 ou na ultima poltrona nao separa nada — seria
        um espaco na borda do bloco, nao uma passagem."""
        fora = [c for c in self.aisles if not 0 < c < self.seats_per_row]
        if fora:
            raise ValueError(
                f"Corredores precisam ficar entre 1 e {self.seats_per_row - 1}: "
                f"{', '.join(map(str, fora))}"
            )
        return self


class SectorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    rows: int
    seats_per_row: int
    display_order: int
    capacity: int
    special_seats: list[SpecialSeatOut]
    aisles: list[int]


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


class RoomUpdate(BaseModel):
    """Alteração parcial. Campo ausente fica como está.

    `sectors` só é aceito enquanto a sala não tiver nenhuma sessão. Ver
    decisão D29.
    """

    name: str | None = Field(None, min_length=1, max_length=80)
    location: str | None = Field(None, max_length=160)
    sectors: list[SectorIn] | None = Field(None, min_length=1)

    @field_validator("name")
    @classmethod
    def limpa_nome(cls, v: str | None) -> str | None:
        return v.strip() if v else v

    @field_validator("sectors")
    @classmethod
    def nomes_de_setor_unicos(cls, v: list[SectorIn] | None) -> list[SectorIn] | None:
        if v is None:
            return v
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
