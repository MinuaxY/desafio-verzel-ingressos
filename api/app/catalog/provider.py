"""Contrato do provedor de catálogo."""
from typing import Protocol

from app.catalog.schemas import CatalogItem, CatalogPage


class CatalogUnavailable(Exception):
    """O provedor externo falhou: rede, timeout, chave inválida ou rate limit."""


class CatalogProvider(Protocol):
    def search(self, query: str, page: int = 1) -> CatalogPage: ...

    def get(self, item_id: str) -> CatalogItem | None: ...
