"""Escolhe o provedor de catálogo conforme a configuração."""
from functools import lru_cache

from app.catalog.fixture import FixtureProvider
from app.catalog.provider import CatalogProvider
from app.catalog.tmdb import TmdbProvider
from app.config import get_settings

PROVEDORES = {"tmdb": TmdbProvider, "fixture": FixtureProvider}


@lru_cache
def get_catalog_provider() -> CatalogProvider:
    settings = get_settings()
    escolhido = settings.catalog_provider.lower()

    if escolhido not in PROVEDORES:
        raise ValueError(
            f"CATALOG_PROVIDER inválido: {settings.catalog_provider!r}. "
            f"Use um de: {', '.join(PROVEDORES)}"
        )

    # Sem token configurado, o TMDb responderia 401 em toda chamada. Cair no
    # provedor local é melhor que subir uma aplicação que falha no primeiro clique.
    if escolhido == "tmdb" and not settings.tmdb_read_token:
        return FixtureProvider(settings)

    return PROVEDORES[escolhido](settings)
