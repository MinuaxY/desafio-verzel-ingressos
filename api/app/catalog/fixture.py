"""Provedor de catálogo servido de arquivo local.

Existe por dois motivos. Primeiro, testes e desenvolvimento não devem depender
de rede, de chave nem de rate limit. Segundo, a aplicação continua demonstrável
se a API externa estiver fora do ar no momento de uma avaliação.

Os dados foram capturados de chamadas reais ao TMDb, então o formato é o mesmo
que o provedor real entrega. Ver decisão D8.
"""
import json
import unicodedata
from functools import lru_cache
from pathlib import Path

from app.catalog.schemas import CatalogItem, CatalogPage

ARQUIVO = Path(__file__).parent / "fixture_data.json"
POR_PAGINA = 20


def _sem_acento(texto: str) -> str:
    normalizado = unicodedata.normalize("NFD", texto.casefold())
    return "".join(c for c in normalizado if unicodedata.category(c) != "Mn")


@lru_cache
def _load() -> list[CatalogItem]:
    data = json.loads(ARQUIVO.read_text(encoding="utf-8"))
    return [CatalogItem(**i) for i in data["items"]]


class FixtureProvider:
    def __init__(self, *_args, **_kwargs) -> None:
        self.items = _load()

    def search(self, query: str, page: int = 1) -> CatalogPage:
        term = _sem_acento(query.strip())
        encontrados = (
            [i for i in self.items if term in _sem_acento(i.title)] if term else list(self.items)
        )
        inicio = (page - 1) * POR_PAGINA
        return CatalogPage(
            items=encontrados[inicio : inicio + POR_PAGINA],
            page=page,
            total_pages=max(1, -(-len(encontrados) // POR_PAGINA)),
            total_results=len(encontrados),
        )

    def get(self, item_id: str) -> CatalogItem | None:
        return next((i for i in self.items if i.id == item_id), None)
