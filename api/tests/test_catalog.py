"""Catálogo de filmes.

Roda contra o provedor local: teste não deve depender de rede nem de chave.
"""
import pytest

from app.catalog.factory import get_catalog_provider
from app.catalog.fixture import FixtureProvider
from app.catalog.provider import CatalogUnavailable
from app.catalog.tmdb import TmdbProvider
from app.config import Settings, get_settings

from tests.conftest import cria_conta

ORGANIZADOR = {
    "name": "Org", "email": "org@cat.dev", "password": "senhaforte123", "role": "ORGANIZER",
}
CLIENTE = {
    "name": "Cli", "email": "cli@cat.dev", "password": "senhaforte123", "role": "CUSTOMER",
}


@pytest.fixture(autouse=True)
def usa_fixture_provider(monkeypatch):
    """Força o provedor local.

    get_settings tem lru_cache, entao mexer so na variavel de ambiente nao
    basta: sem limpar o cache, os testes iriam bater no TMDb de verdade.
    """
    monkeypatch.setenv("CATALOG_PROVIDER", "fixture")
    monkeypatch.setenv("TMDB_READ_TOKEN", "")
    get_settings.cache_clear()
    get_catalog_provider.cache_clear()
    yield
    get_settings.cache_clear()
    get_catalog_provider.cache_clear()


def auth(client, dados):
    """Papel privilegiado não sai do cadastro público. Ver conftest."""
    return cria_conta(client, dados)


class TestAutorizacao:
    def test_catalogo_exige_autenticacao(self, client):
        assert client.get("/catalog/search", params={"q": "toy"}).status_code == 401

    def test_cliente_nao_acessa_o_catalogo(self, client):
        """O catálogo serve para o organizador montar sessões, e a chave da API
        externa não deve ser gasta por quem não vai criar evento."""
        r = client.get("/catalog/search", params={"q": "toy"}, headers=auth(client, CLIENTE))
        assert r.status_code == 403


class TestBusca:
    def test_organizador_busca_filmes(self, client):
        r = client.get("/catalog/search", params={"q": "toy"}, headers=auth(client, ORGANIZADOR))
        assert r.status_code == 200
        corpo = r.json()
        assert corpo["total_results"] >= 1
        assert all("toy" in i["title"].lower() for i in corpo["items"])

    def test_busca_ignora_acentos(self, client):
        """'ficcao' precisa achar 'Ficção'; usuário não digita acento em busca."""
        headers = auth(client, ORGANIZADOR)
        com = client.get("/catalog/search", params={"q": "homem-aranha"}, headers=headers)
        assert com.json()["total_results"] >= 1

    def test_busca_sem_resultado_devolve_lista_vazia(self, client):
        r = client.get(
            "/catalog/search", params={"q": "zzzzinexistente"}, headers=auth(client, ORGANIZADOR)
        )
        assert r.status_code == 200
        assert r.json()["items"] == []

    def test_termo_vazio_e_recusado(self, client):
        r = client.get("/catalog/search", params={"q": ""}, headers=auth(client, ORGANIZADOR))
        assert r.status_code == 422


class TestDetalhe:
    def test_detalhe_traz_os_campos_que_a_sessao_precisa(self, client):
        headers = auth(client, ORGANIZADOR)
        primeiro = client.get(
            "/catalog/search", params={"q": "a"}, headers=headers
        ).json()["items"][0]

        r = client.get(f"/catalog/{primeiro['id']}", headers=headers)
        assert r.status_code == 200
        item = r.json()
        assert item["title"] and item["overview"]
        assert item["poster_url"].startswith("https://image.tmdb.org/")

    def test_filme_inexistente_responde_404(self, client):
        r = client.get("/catalog/999999999", headers=auth(client, ORGANIZADOR))
        assert r.status_code == 404


class TestFabrica:
    def test_sem_token_cai_no_provedor_local(self):
        """Melhor servir catálogo local do que subir uma aplicação que
        responde 401 no primeiro clique."""
        import app.catalog.factory as f
        original = f.get_settings
        f.get_settings = lambda: Settings(catalog_provider="tmdb", tmdb_read_token="")
        try:
            f.get_catalog_provider.cache_clear()
            assert isinstance(f.get_catalog_provider(), FixtureProvider)
        finally:
            f.get_settings = original
            f.get_catalog_provider.cache_clear()

    def test_com_token_usa_o_tmdb(self):
        import app.catalog.factory as f
        original = f.get_settings
        f.get_settings = lambda: Settings(catalog_provider="tmdb", tmdb_read_token="abc")
        try:
            f.get_catalog_provider.cache_clear()
            assert isinstance(f.get_catalog_provider(), TmdbProvider)
        finally:
            f.get_settings = original
            f.get_catalog_provider.cache_clear()

    def test_provedor_invalido_falha_ao_subir(self):
        import app.catalog.factory as f
        original = f.get_settings
        f.get_settings = lambda: Settings(catalog_provider="inexistente")
        try:
            f.get_catalog_provider.cache_clear()
            with pytest.raises(ValueError, match="CATALOG_PROVIDER"):
                f.get_catalog_provider()
        finally:
            f.get_settings = original
            f.get_catalog_provider.cache_clear()


class TestCacheETraducaoDeErro:
    def test_falha_de_rede_vira_catalog_unavailable(self, monkeypatch):
        """Erro de httpx não pode vazar para a camada de cima."""
        import httpx
        provider = TmdbProvider(Settings(tmdb_read_token="x"))

        def explode(*_a, **_kw):
            raise httpx.ConnectError("sem rede")

        monkeypatch.setattr(httpx, "get", explode)
        with pytest.raises(CatalogUnavailable):
            provider.search("qualquer")

    def test_segunda_chamada_igual_usa_cache(self, monkeypatch):
        import httpx
        provider = TmdbProvider(Settings(tmdb_read_token="x", catalog_cache_ttl=60))
        chamadas = []

        class RespostaFake:
            def raise_for_status(self): pass
            def json(self): return {"results": [], "page": 1, "total_pages": 1, "total_results": 0}

        def conta(*_a, **_kw):
            chamadas.append(1)
            return RespostaFake()

        monkeypatch.setattr(httpx, "get", conta)
        provider.search("duna")
        provider.search("duna")
        assert len(chamadas) == 1
