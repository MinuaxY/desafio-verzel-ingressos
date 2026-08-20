"""Consulta ao catálogo de filmes.

Restrito ao organizador: é ele quem monta sessões a partir do catálogo. Manter
a rota fechada também evita que a chave da API externa seja consumida por
tráfego anônimo.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.catalog.factory import get_catalog_provider
from app.catalog.provider import CatalogUnavailable
from app.catalog.schemas import CatalogItem, CatalogPage
from app.core.deps import require_role
from app.models.user import Role

router = APIRouter(
    prefix="/catalog",
    tags=["Catálogo"],
    dependencies=[Depends(require_role(Role.ORGANIZER))],
)


@router.get("/search", response_model=CatalogPage)
def search(
    q: str = Query(min_length=1, description="Termo de busca"),
    page: int = Query(1, ge=1),
) -> CatalogPage:
    try:
        return get_catalog_provider().search(q, page)
    except CatalogUnavailable as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e))


@router.get("/{item_id}", response_model=CatalogItem)
def detail(item_id: str) -> CatalogItem:
    try:
        item = get_catalog_provider().get(item_id)
    except CatalogUnavailable as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e))
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Filme não encontrado no catálogo")
    return item
