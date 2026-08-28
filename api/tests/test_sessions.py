"""Sessões: criação pelo organizador e vitrine pública."""
from datetime import datetime, timedelta, timezone

import pytest

from app.catalog.factory import get_catalog_provider
from app.catalog.fixture import FixtureProvider
from app.config import get_settings

from tests.conftest import cria_conta

ORGANIZADOR = {
    "name": "Org", "email": "org@ses.dev", "password": "senhaforte123", "role": "ORGANIZER",
}
OUTRO_ORGANIZADOR = {
    "name": "Org2", "email": "org2@ses.dev", "password": "senhaforte123", "role": "ORGANIZER",
}
CLIENTE = {
    "name": "Cli", "email": "cli@ses.dev", "password": "senhaforte123", "role": "CUSTOMER",
}

SALA = {
    "name": "Sala A",
    "location": "Centro",
    "sectors": [
        {"name": "Plateia", "rows": 4, "seats_per_row": 8, "display_order": 0},
        {"name": "VIP", "rows": 1, "seats_per_row": 4, "display_order": 1},
    ],
}


@pytest.fixture(autouse=True)
def usa_fixture_provider(monkeypatch):
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


def futuro(dias: int = 2, hora: int = 20) -> str:
    quando = datetime.now(timezone.utc) + timedelta(days=dias)
    return quando.replace(hour=hora, minute=0, second=0, microsecond=0).isoformat()


def um_filme() -> str:
    return FixtureProvider().items[0].id


def cria_sala(client, headers) -> dict:
    return client.post("/rooms", json=SALA, headers=headers).json()


def payload_sessao(sala: dict, **extra) -> dict:
    return {
        "catalog_id": um_filme(),
        "room_id": sala["id"],
        "starts_at": futuro(),
        "prices": [
            {"sector_id": s["id"], "price_cents": 3000 if s["name"] == "Plateia" else 5000}
            for s in sala["sectors"]
        ],
        **extra,
    }


class TestCriacao:
    def test_cria_sessao_como_rascunho(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)

        r = client.post("/organizer/sessions", json=payload_sessao(sala), headers=headers)
        assert r.status_code == 201
        assert r.json()["status"] == "DRAFT"

    def test_cria_ja_publicada(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        r = client.post(
            "/organizer/sessions", json=payload_sessao(sala, publish=True), headers=headers
        )
        assert r.json()["status"] == "PUBLISHED"

    def test_guarda_copia_dos_dados_do_filme(self, client):
        """O ingresso é documento, não consulta ao vivo: a sessão precisa
        sobreviver ao catálogo externo mudar ou sair do ar."""
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        r = client.post("/organizer/sessions", json=payload_sessao(sala), headers=headers)

        filme = r.json()["movie"]
        esperado = FixtureProvider().items[0]
        assert filme["title"] == esperado.title
        assert filme["poster_url"] == esperado.poster_url
        assert filme["runtime_minutes"] == esperado.runtime_minutes

    def test_capacidade_vem_da_sala(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        r = client.post("/organizer/sessions", json=payload_sessao(sala), headers=headers)
        assert r.json()["capacity"] == 36  # 4x8 + 1x4

    def test_faixa_de_precos(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        corpo = client.post(
            "/organizer/sessions", json=payload_sessao(sala), headers=headers
        ).json()
        assert corpo["min_price_cents"] == 3000
        assert corpo["max_price_cents"] == 5000


class TestValidacoes:
    def test_horario_no_passado_e_recusado(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        passado = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        r = client.post(
            "/organizer/sessions",
            json=payload_sessao(sala, starts_at=passado),
            headers=headers,
        )
        assert r.status_code == 422

    def test_horario_sem_fuso_e_recusado(self, client):
        """Sem fuso não dá para saber que instante é esse."""
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        r = client.post(
            "/organizer/sessions",
            json=payload_sessao(sala, starts_at="2027-01-01T20:00:00"),
            headers=headers,
        )
        assert r.status_code == 422

    def test_mesma_sala_no_mesmo_horario_e_recusada(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        corpo = payload_sessao(sala)
        assert client.post("/organizer/sessions", json=corpo, headers=headers).status_code == 201
        r = client.post("/organizer/sessions", json=corpo, headers=headers)
        assert r.status_code == 409

    def test_setor_sem_preco_e_recusado(self, client):
        """Sem essa trava a sessão iria ao ar com um setor sem valor, e o erro
        só apareceria quando alguém tentasse comprar aquela poltrona."""
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        corpo = payload_sessao(sala)
        corpo["prices"] = corpo["prices"][:1]

        r = client.post("/organizer/sessions", json=corpo, headers=headers)
        assert r.status_code == 422
        assert "VIP" in r.json()["detail"]

    def test_preco_duplicado_para_o_mesmo_setor_e_recusado(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        corpo = payload_sessao(sala)
        corpo["prices"] = [corpo["prices"][0], corpo["prices"][0]]
        assert client.post("/organizer/sessions", json=corpo, headers=headers).status_code == 422

    def test_filme_inexistente_e_recusado(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        r = client.post(
            "/organizer/sessions",
            json=payload_sessao(sala, catalog_id="000000"),
            headers=headers,
        )
        assert r.status_code == 404

    def test_sala_de_outro_organizador_e_recusada(self, client):
        sala = cria_sala(client, auth(client, ORGANIZADOR))
        r = client.post(
            "/organizer/sessions",
            json=payload_sessao(sala),
            headers=auth(client, OUTRO_ORGANIZADOR),
        )
        assert r.status_code == 404


class TestCicloDeVida:
    def test_publicar_e_despublicar(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = client.post(
            "/organizer/sessions", json=payload_sessao(sala), headers=headers
        ).json()

        publicada = client.post(f"/organizer/sessions/{sessao['id']}/publish", headers=headers)
        assert publicada.json()["status"] == "PUBLISHED"

        oculta = client.post(f"/organizer/sessions/{sessao['id']}/unpublish", headers=headers)
        assert oculta.json()["status"] == "DRAFT"

    def test_sessao_cancelada_nao_volta_atras(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = client.post(
            "/organizer/sessions", json=payload_sessao(sala), headers=headers
        ).json()

        client.post(f"/organizer/sessions/{sessao['id']}/cancel", headers=headers)
        r = client.post(f"/organizer/sessions/{sessao['id']}/publish", headers=headers)
        assert r.status_code == 409

    def test_atualiza_precos(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = client.post(
            "/organizer/sessions", json=payload_sessao(sala), headers=headers
        ).json()

        novos = [{"sector_id": s["id"], "price_cents": 9900} for s in sala["sectors"]]
        r = client.patch(
            f"/organizer/sessions/{sessao['id']}", json={"prices": novos}, headers=headers
        )
        assert r.status_code == 200
        assert r.json()["min_price_cents"] == 9900


class TestVitrinePublica:
    """A vitrine é aberta: quem não tem conta vê o que está em cartaz.
    Ver decisão D10."""

    def test_lista_sem_autenticacao(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        client.post(
            "/organizer/sessions", json=payload_sessao(sala, publish=True), headers=headers
        )

        r = client.get("/sessions")
        assert r.status_code == 200
        assert r.json()["total"] == 1

    def test_rascunho_nao_aparece(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        client.post("/organizer/sessions", json=payload_sessao(sala), headers=headers)
        assert client.get("/sessions").json()["total"] == 0

    def test_cancelada_nao_aparece(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = client.post(
            "/organizer/sessions", json=payload_sessao(sala, publish=True), headers=headers
        ).json()

        client.post(f"/organizer/sessions/{sessao['id']}/cancel", headers=headers)
        assert client.get("/sessions").json()["total"] == 0

    def test_busca_por_titulo(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        client.post(
            "/organizer/sessions", json=payload_sessao(sala, publish=True), headers=headers
        )

        titulo = FixtureProvider().items[0].title
        assert client.get("/sessions", params={"busca": titulo[:6]}).json()["total"] == 1
        assert client.get("/sessions", params={"busca": "zzzznada"}).json()["total"] == 0

    def test_detalhe_publico_traz_setores_e_precos(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = client.post(
            "/organizer/sessions", json=payload_sessao(sala, publish=True), headers=headers
        ).json()

        r = client.get(f"/sessions/{sessao['id']}")
        assert r.status_code == 200
        corpo = r.json()
        assert [p["sector"]["name"] for p in corpo["prices"]] == ["Plateia", "VIP"]
        assert corpo["capacity"] == 36

    def test_detalhe_de_rascunho_responde_404(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = client.post(
            "/organizer/sessions", json=payload_sessao(sala), headers=headers
        ).json()
        assert client.get(f"/sessions/{sessao['id']}").status_code == 404
