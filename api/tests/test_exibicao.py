"""Classificação indicativa e formato de exibição.

Duas informações que a vitrine mostra e que vêm de origens diferentes: a
classificação é do filme e chega pelo catálogo; áudio e formato são desta
sessão e são escolha de quem publica.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.catalog.factory import get_catalog_provider
from app.catalog.fixture import FixtureProvider
from app.catalog.tmdb import _classificacao_brasileira
from app.config import get_settings

from tests.conftest import cria_conta

ORGANIZADOR = {
    "name": "Org", "email": "org@exib.dev", "password": "senhaforte123", "role": "ORGANIZER",
}
SALA = {"name": "Sala Exib", "sectors": [{"name": "Plateia", "rows": 2, "seats_per_row": 4}]}


@pytest.fixture(autouse=True)
def usa_fixture_provider(monkeypatch):
    monkeypatch.setenv("CATALOG_PROVIDER", "fixture")
    monkeypatch.setenv("TMDB_READ_TOKEN", "")
    get_settings.cache_clear()
    get_catalog_provider.cache_clear()
    yield
    get_settings.cache_clear()
    get_catalog_provider.cache_clear()


def auth(client, data):
    """Papel privilegiado não sai do cadastro público. Ver conftest."""
    return cria_conta(client, data)


def cria_sessao(client, headers, room, movie, **extra):
    starts_at = (datetime.now(timezone.utc) + timedelta(days=2, hours=extra.pop("h", 0)))
    return client.post(
        "/organizer/sessions",
        json={
            "catalog_id": movie.id,
            "room_id": room["id"],
            "starts_at": starts_at.replace(microsecond=0).isoformat(),
            "prices": [{"sector_id": room["sectors"][0]["id"], "price_cents": 3000}],
            "publish": True,
            **extra,
        },
        headers=headers,
    )


class TestExtracaoDaClassificacao:
    """O TMDb devolve várias classificações por filme, uma por tipo de
    lançamento. Para cinema vale a de exibição em sala."""

    def test_prefere_a_de_cinema(self):
        bruto = {"results": [{"iso_3166_1": "BR", "release_dates": [
            {"certification": "12", "type": 4},  # digital
            {"certification": "14", "type": 3},  # cinema
        ]}]}
        assert _classificacao_brasileira(bruto) == "14"

    def test_ignora_certificacao_vazia(self):
        bruto = {"results": [{"iso_3166_1": "BR", "release_dates": [
            {"certification": "", "type": 3},
            {"certification": "16", "type": 4},
        ]}]}
        assert _classificacao_brasileira(bruto) == "16"

    def test_ignora_outros_paises(self):
        bruto = {"results": [{"iso_3166_1": "US", "release_dates": [
            {"certification": "R", "type": 3},
        ]}]}
        assert _classificacao_brasileira(bruto) is None

    @pytest.mark.parametrize("payload", [None, {}, {"results": []}])
    def test_ausencia_de_dado_nao_quebra(self, payload):
        assert _classificacao_brasileira(payload) is None


class TestClassificacaoNaSessao:
    def test_e_copiada_do_catalogo(self, client):
        headers = auth(client, ORGANIZADOR)
        room = client.post("/rooms", json=SALA, headers=headers).json()
        movie = next(f for f in FixtureProvider().items if f.age_rating)

        r = cria_sessao(client, headers, room, movie)
        assert r.status_code == 201
        assert r.json()["movie"]["age_rating"] == movie.age_rating

    def test_filme_sem_classificacao_nao_impede_a_sessao(self, client):
        """Nem todo filme tem classificação brasileira registrada, e isso não
        pode travar a publicação."""
        headers = auth(client, ORGANIZADOR)
        room = client.post("/rooms", json=SALA, headers=headers).json()
        sem = next((f for f in FixtureProvider().items if not f.age_rating), None)
        if sem is None:
            pytest.skip("o fixture atual não tem filme sem classificação")

        r = cria_sessao(client, headers, room, sem)
        assert r.status_code == 201
        assert r.json()["movie"]["age_rating"] is None

    def test_aparece_na_vitrine_publica(self, client):
        headers = auth(client, ORGANIZADOR)
        room = client.post("/rooms", json=SALA, headers=headers).json()
        movie = next(f for f in FixtureProvider().items if f.age_rating)
        cria_sessao(client, headers, room, movie)

        item = client.get("/sessions").json()["items"][0]
        assert item["age_rating"] == movie.age_rating


class TestFormatoDaSessao:
    def test_padrao_e_legendado_2d(self, client):
        headers = auth(client, ORGANIZADOR)
        room = client.post("/rooms", json=SALA, headers=headers).json()
        corpo = cria_sessao(client, headers, room, FixtureProvider().items[0]).json()
        assert corpo["audio"] == "SUBTITLED"
        assert corpo["screen_format"] == "TWO_D"

    @pytest.mark.parametrize(
        "audio,formato", [("DUBBED", "THREE_D"), ("NATIONAL", "TWO_D"), ("SUBTITLED", "THREE_D")]
    )
    def test_respeita_a_escolha_do_organizador(self, client, audio, formato):
        headers = auth(client, ORGANIZADOR)
        room = client.post("/rooms", json=SALA, headers=headers).json()
        corpo = cria_sessao(
            client, headers, room, FixtureProvider().items[0], audio=audio, screen_format=formato
        ).json()
        assert corpo["audio"] == audio
        assert corpo["screen_format"] == formato

    def test_valor_invalido_e_recusado(self, client):
        headers = auth(client, ORGANIZADOR)
        room = client.post("/rooms", json=SALA, headers=headers).json()
        r = cria_sessao(client, headers, room, FixtureProvider().items[0], audio="CANTADO")
        assert r.status_code == 422

    def test_mesmo_filme_com_sessoes_diferentes(self, client):
        """É o ponto de áudio e formato serem da sessão: o mesmo título roda
        dublado num horário e legendado noutro."""
        headers = auth(client, ORGANIZADOR)
        room = client.post("/rooms", json=SALA, headers=headers).json()
        movie = FixtureProvider().items[0]

        a = cria_sessao(client, headers, room, movie, h=0, audio="DUBBED")
        b = cria_sessao(client, headers, room, movie, h=3, audio="SUBTITLED")

        assert a.status_code == b.status_code == 201
        assert a.json()["movie"]["title"] == b.json()["movie"]["title"]
        assert a.json()["audio"] != b.json()["audio"]

    def test_pode_ser_alterado_depois(self, client):
        headers = auth(client, ORGANIZADOR)
        room = client.post("/rooms", json=SALA, headers=headers).json()
        session = cria_sessao(client, headers, room, FixtureProvider().items[0]).json()

        r = client.patch(
            f"/organizer/sessions/{session['id']}",
            json={"audio": "DUBBED", "screen_format": "THREE_D"},
            headers=headers,
        )
        assert r.status_code == 200
        assert r.json()["audio"] == "DUBBED"
        assert r.json()["screen_format"] == "THREE_D"
