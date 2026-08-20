"""Provedor de catálogo apoiado no TMDb."""
import httpx

from app.catalog.cache import TTLCache
from app.catalog.provider import CatalogUnavailable
from app.catalog.schemas import CatalogItem, CatalogPage
from app.config import Settings

TAMANHO_POSTER = "w500"
TAMANHO_BACKDROP = "w1280"


class TmdbProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.cache = TTLCache(settings.catalog_cache_ttl)

    # -- infraestrutura ----------------------------------------------------

    def _get(self, path: str, params: dict[str, str | int] | None = None) -> dict:
        chave = f"{path}?{sorted((params or {}).items())}"
        if (cacheado := self.cache.get(chave)) is not None:
            return cacheado

        try:
            resposta = httpx.get(
                f"{self.settings.tmdb_base_url}{path}",
                params={"language": self.settings.tmdb_language, **(params or {})},
                headers={
                    "Authorization": f"Bearer {self.settings.tmdb_read_token}",
                    "accept": "application/json",
                },
                timeout=10.0,
            )
            resposta.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise CatalogUnavailable(
                f"O catálogo respondeu {e.response.status_code}"
            ) from e
        except httpx.HTTPError as e:
            raise CatalogUnavailable("Não foi possível falar com o catálogo") from e

        dados = resposta.json()
        self.cache.set(chave, dados)
        return dados

    def _imagem(self, path: str | None, tamanho: str) -> str | None:
        if not path:
            return None
        return f"{self.settings.tmdb_image_base_url}/{tamanho}{path}"

    def _para_item(self, bruto: dict) -> CatalogItem:
        lancamento = (bruto.get("release_date") or "")[:4]
        generos = bruto.get("genres")
        return CatalogItem(
            id=str(bruto["id"]),
            title=bruto.get("title") or bruto.get("original_title") or "Sem título",
            original_title=bruto.get("original_title"),
            overview=bruto.get("overview") or None,
            release_year=int(lancamento) if lancamento.isdigit() else None,
            poster_url=self._imagem(bruto.get("poster_path"), TAMANHO_POSTER),
            backdrop_url=self._imagem(bruto.get("backdrop_path"), TAMANHO_BACKDROP),
            rating=round(bruto["vote_average"], 1) if bruto.get("vote_average") else None,
            runtime_minutes=bruto.get("runtime"),
            genres=[g["name"] for g in generos] if generos else [],
        )

    # -- contrato ----------------------------------------------------------

    def search(self, query: str, page: int = 1) -> CatalogPage:
        dados = self._get("/search/movie", {"query": query, "page": page})
        return CatalogPage(
            items=[self._para_item(r) for r in dados.get("results", [])],
            page=dados.get("page", 1),
            total_pages=dados.get("total_pages", 1),
            total_results=dados.get("total_results", 0),
        )

    def get(self, item_id: str) -> CatalogItem | None:
        try:
            return self._para_item(self._get(f"/movie/{item_id}"))
        except CatalogUnavailable as e:
            # 404 do TMDb significa filme inexistente, não indisponibilidade.
            if "404" in str(e):
                return None
            raise
