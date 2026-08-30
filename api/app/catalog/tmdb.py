"""Provedor de catálogo apoiado no TMDb."""
import httpx

from app.catalog.cache import TTLCache
from app.catalog.provider import CatalogUnavailable
from app.catalog.schemas import CatalogItem, CatalogPage
from app.config import Settings

TAMANHO_POSTER = "w500"
TAMANHO_BACKDROP = "w1280"

# O TMDb separa os lançamentos por tipo, e cada um pode ter classificação
# diferente: Duna é 14 no cinema e 12 no digital. Para sessão de cinema vale a
# de exibição em sala, então esses tipos vêm primeiro na ordem de preferência.
CINEMA_GENRE = (3, 2, 1)  # geral, limitado, pré-estreia


def _classificacao_brasileira(release_dates: dict | None) -> str | None:
    """Extrai a classificação indicativa do Brasil, preferindo a de cinema."""
    if not release_dates:
        return None

    br = next(
        (r for r in release_dates.get("results", []) if r.get("iso_3166_1") == "BR"), None
    )
    if not br:
        return None

    lancamentos = [r for r in br.get("release_dates", []) if r.get("certification")]
    if not lancamentos:
        return None

    lancamentos.sort(
        key=lambda r: CINEMA_GENRE.index(r["type"]) if r["type"] in CINEMA_GENRE else 99
    )
    return lancamentos[0]["certification"].strip() or None


class TmdbProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.cache = TTLCache(settings.catalog_cache_ttl)

    # -- infraestrutura ----------------------------------------------------

    def _get(self, path: str, params: dict[str, str | int] | None = None) -> dict:
        key = f"{path}?{sorted((params or {}).items())}"
        if (cacheado := self.cache.get(key)) is not None:
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

        data = resposta.json()
        self.cache.set(key, data)
        return data

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
            age_rating=_classificacao_brasileira(bruto.get("release_dates")),
        )

    # -- contrato ----------------------------------------------------------

    def search(self, query: str, page: int = 1) -> CatalogPage:
        data = self._get("/search/movie", {"query": query, "page": page})
        return CatalogPage(
            items=[self._para_item(r) for r in data.get("results", [])],
            page=data.get("page", 1),
            total_pages=data.get("total_pages", 1),
            total_results=data.get("total_results", 0),
        )

    def get(self, item_id: str) -> CatalogItem | None:
        try:
            # append_to_response traz a classificação na mesma requisição,
            # em vez de gastar uma segunda chamada por filme.
            return self._para_item(
                self._get(f"/movie/{item_id}", {"append_to_response": "release_dates"})
            )
        except CatalogUnavailable as e:
            # 404 do TMDb significa filme inexistente, não indisponibilidade.
            if "404" in str(e):
                return None
            raise
