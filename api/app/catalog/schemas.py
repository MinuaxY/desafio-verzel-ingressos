"""Modelo normalizado do catálogo.

A aplicação não conhece o formato do TMDb. Tudo que vem de fora é traduzido
para estes contratos, e é só isto que o resto do sistema enxerga — trocar de
provedor não deve vazar para os models nem para o front. Ver decisão D8.
"""
from pydantic import BaseModel


class CatalogItem(BaseModel):
    id: str
    title: str
    original_title: str | None = None
    overview: str | None = None
    release_year: int | None = None
    poster_url: str | None = None
    backdrop_url: str | None = None
    rating: float | None = None
    runtime_minutes: int | None = None
    genres: list[str] = []


class CatalogPage(BaseModel):
    items: list[CatalogItem]
    page: int
    total_pages: int
    total_results: int
