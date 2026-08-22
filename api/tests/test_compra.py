"""Compra: mapa de assentos, reserva, pagamento e emissão do ingresso."""
from datetime import datetime, timedelta, timezone

import pytest

from app.catalog.factory import get_catalog_provider
from app.catalog.fixture import FixtureProvider
from app.config import get_settings

ORGANIZADOR = {
    "name": "Org", "email": "org@compra.dev", "password": "senhaforte123", "role": "ORGANIZER",
}
CLIENTE = {
    "name": "Cli", "email": "cli@compra.dev", "password": "senhaforte123", "role": "CUSTOMER",
}
OUTRO_CLIENTE = {
    "name": "Cli2", "email": "cli2@compra.dev", "password": "senhaforte123", "role": "CUSTOMER",
}
PORTEIRO = {
    "name": "Gate", "email": "gate@compra.dev", "password": "senhaforte123", "role": "GATE",
}

CARTAO_OK = {"card_number": "4111111111111111", "card_holder": "PAULO V"}
CARTAO_RECUSA = {"card_number": "4000000000000002", "card_holder": "PAULO V"}
CARTAO_SEM_SALDO = {"card_number": "4000000000009995", "card_holder": "PAULO V"}

SALA = {
    "name": "Sala Compra",
    "location": "Centro",
    "sectors": [
        {
            "name": "Plateia",
            "rows": 3,
            "seats_per_row": 6,
            "display_order": 0,
            "special_seats": [
                {"seat_code": "A1", "kind": "WHEELCHAIR"},
                {"seat_code": "A2", "kind": "COMPANION"},
            ],
        },
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
    token = client.post("/auth/register", json=dados).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def cenario(client):
    """Uma sessão publicada, com sala de 22 lugares, pronta para comprar."""
    org = auth(client, ORGANIZADOR)
    sala = client.post("/rooms", json=SALA, headers=org).json()
    quando = (datetime.now(timezone.utc) + timedelta(days=2)).replace(microsecond=0)

    sessao = client.post(
        "/organizer/sessions",
        json={
            "catalog_id": FixtureProvider().items[0].id,
            "room_id": sala["id"],
            "starts_at": quando.isoformat(),
            "prices": [
                {"sector_id": s["id"], "price_cents": 3000 if s["name"] == "Plateia" else 5000}
                for s in sala["sectors"]
            ],
            "publish": True,
        },
        headers=org,
    ).json()

    setores = {s["name"]: s["id"] for s in sala["sectors"]}
    return {
        "org": org,
        "sala": sala,
        "sessao": sessao,
        "plateia": setores["Plateia"],
        "vip": setores["VIP"],
        "cliente": auth(client, CLIENTE),
    }


def reserva(client, cenario, assentos, headers=None):
    return client.post(
        "/orders",
        json={"session_id": cenario["sessao"]["id"], "seats": assentos},
        headers=headers or cenario["cliente"],
    )


class TestMapaDeAssentos:
    def test_mapa_e_publico(self, client, cenario):
        r = client.get(f"/sessions/{cenario['sessao']['id']}/seats")
        assert r.status_code == 200

    def test_mapa_traz_a_geometria_completa(self, client, cenario):
        corpo = client.get(f"/sessions/{cenario['sessao']['id']}/seats").json()
        assert corpo["capacity"] == 22
        assert corpo["available"] == 22

        plateia = corpo["sectors"][0]
        assert plateia["name"] == "Plateia"
        assert len(plateia["seats"]) == 18
        assert plateia["seats"][0]["code"] == "A1"
        assert plateia["seats"][-1]["code"] == "C6"

    def test_mapa_marca_as_poltronas_acessiveis(self, client, cenario):
        plateia = client.get(f"/sessions/{cenario['sessao']['id']}/seats").json()["sectors"][0]
        tipos = {s["code"]: s["kind"] for s in plateia["seats"] if s["kind"]}
        assert tipos == {"A1": "WHEELCHAIR", "A2": "COMPANION"}

    def test_assento_reservado_aparece_ocupado(self, client, cenario):
        reserva(client, cenario, [{"sector_id": cenario["plateia"], "seat_code": "B3"}])

        corpo = client.get(f"/sessions/{cenario['sessao']['id']}/seats").json()
        assert corpo["available"] == 21
        b3 = next(s for s in corpo["sectors"][0]["seats"] if s["code"] == "B3")
        assert b3["taken"] is True

    def test_preco_por_setor_aparece_no_mapa(self, client, cenario):
        setores = client.get(f"/sessions/{cenario['sessao']['id']}/seats").json()["sectors"]
        assert {s["name"]: s["price_cents"] for s in setores} == {"Plateia": 3000, "VIP": 5000}


class TestReserva:
    def test_exige_autenticacao(self, client, cenario):
        r = client.post(
            "/orders",
            json={"session_id": cenario["sessao"]["id"], "seats": [
                {"sector_id": cenario["plateia"], "seat_code": "A3"}
            ]},
        )
        assert r.status_code == 401

    def test_organizador_nao_compra(self, client, cenario):
        r = reserva(
            client, cenario,
            [{"sector_id": cenario["plateia"], "seat_code": "A3"}],
            headers=cenario["org"],
        )
        assert r.status_code == 403

    def test_reserva_nasce_pendente(self, client, cenario):
        r = reserva(client, cenario, [{"sector_id": cenario["plateia"], "seat_code": "A3"}])
        assert r.status_code == 201
        assert r.json()["status"] == "PENDING"
        assert r.json()["tickets"][0]["status"] == "RESERVED"

    def test_total_soma_os_setores(self, client, cenario):
        # A Plateia ocupa A a C, entao o VIP comeca em D: as fileiras sao
        # continuas na sala, nao reiniciadas por setor. Ver decisao D23.
        r = reserva(client, cenario, [
            {"sector_id": cenario["plateia"], "seat_code": "A3"},
            {"sector_id": cenario["vip"], "seat_code": "D1"},
        ])
        assert r.json()["total_cents"] == 8000

    def test_reserva_pendente_nao_tem_codigo(self, client, cenario):
        """Sem pagamento não há ingresso, e sem ingresso não há QR."""
        r = reserva(client, cenario, [{"sector_id": cenario["plateia"], "seat_code": "A3"}])
        assert r.json()["tickets"][0]["code"] is None

    def test_assento_ja_ocupado_e_recusado(self, client, cenario):
        reserva(client, cenario, [{"sector_id": cenario["plateia"], "seat_code": "B1"}])
        r = reserva(
            client, cenario,
            [{"sector_id": cenario["plateia"], "seat_code": "B1"}],
            headers=auth(client, OUTRO_CLIENTE),
        )
        assert r.status_code == 409
        assert "B1" in r.json()["detail"]

    @pytest.mark.parametrize("codigo", ["D1", "A7", "Z9"])
    def test_assento_inexistente_e_recusado(self, client, cenario, codigo):
        r = reserva(client, cenario, [{"sector_id": cenario["plateia"], "seat_code": codigo}])
        assert r.status_code == 422

    def test_mesmo_assento_duas_vezes_no_pedido_e_recusado(self, client, cenario):
        r = reserva(client, cenario, [
            {"sector_id": cenario["plateia"], "seat_code": "A3"},
            {"sector_id": cenario["plateia"], "seat_code": "A3"},
        ])
        assert r.status_code == 422

    def test_limite_de_assentos_por_compra(self, client, cenario):
        muitos = [
            {"sector_id": cenario["plateia"], "seat_code": f"A{i}"} for i in range(1, 7)
        ] * 2
        r = reserva(client, cenario, muitos)
        assert r.status_code == 422


class TestPagamento:
    def test_aprovado_emite_ingresso_com_codigo(self, client, cenario):
        pedido = reserva(
            client, cenario, [{"sector_id": cenario["plateia"], "seat_code": "A3"}]
        ).json()

        r = client.post(
            f"/orders/{pedido['id']}/pay", json=CARTAO_OK, headers=cenario["cliente"]
        )
        assert r.status_code == 200
        corpo = r.json()
        assert corpo["status"] == "PAID"
        assert corpo["paid_at"] is not None

        ingresso = corpo["tickets"][0]
        assert ingresso["status"] == "VALID"
        assert ingresso["code"] and "." in ingresso["code"]
        assert ingresso["share_token"]

    @pytest.mark.parametrize(
        "cartao,trecho", [(CARTAO_RECUSA, "recusado"), (CARTAO_SEM_SALDO, "Saldo")]
    )
    def test_recusado_nao_emite_ingresso(self, client, cenario, cartao, trecho):
        pedido = reserva(
            client, cenario, [{"sector_id": cenario["plateia"], "seat_code": "A4"}]
        ).json()

        corpo = client.post(
            f"/orders/{pedido['id']}/pay", json=cartao, headers=cenario["cliente"]
        ).json()

        assert corpo["status"] == "DECLINED"
        assert trecho in corpo["decline_reason"]
        assert corpo["tickets"][0]["status"] == "CANCELLED"
        assert corpo["tickets"][0]["code"] is None

    def test_recusa_devolve_o_assento_ao_estoque(self, client, cenario):
        """O índice único parcial ignora CANCELLED, então a poltrona volta a
        ficar livre sem nenhuma limpeza."""
        pedido = reserva(
            client, cenario, [{"sector_id": cenario["plateia"], "seat_code": "C1"}]
        ).json()
        client.post(f"/orders/{pedido['id']}/pay", json=CARTAO_RECUSA, headers=cenario["cliente"])

        mapa = client.get(f"/sessions/{cenario['sessao']['id']}/seats").json()
        c1 = next(s for s in mapa["sectors"][0]["seats"] if s["code"] == "C1")
        assert c1["taken"] is False

        # E outra pessoa consegue comprar a mesma poltrona.
        r = reserva(
            client, cenario,
            [{"sector_id": cenario["plateia"], "seat_code": "C1"}],
            headers=auth(client, OUTRO_CLIENTE),
        )
        assert r.status_code == 201

    def test_cartao_invalido_e_recusado(self, client, cenario):
        pedido = reserva(
            client, cenario, [{"sector_id": cenario["plateia"], "seat_code": "A5"}]
        ).json()
        r = client.post(
            f"/orders/{pedido['id']}/pay",
            json={"card_number": "123", "card_holder": "X Y"},
            headers=cenario["cliente"],
        )
        assert r.status_code == 422  # nem chega ao serviço: falha na validação de entrada

    def test_nao_paga_duas_vezes(self, client, cenario):
        pedido = reserva(
            client, cenario, [{"sector_id": cenario["plateia"], "seat_code": "A6"}]
        ).json()
        client.post(f"/orders/{pedido['id']}/pay", json=CARTAO_OK, headers=cenario["cliente"])

        r = client.post(
            f"/orders/{pedido['id']}/pay", json=CARTAO_OK, headers=cenario["cliente"]
        )
        assert r.status_code == 409

    def test_pedido_de_outro_cliente_responde_404(self, client, cenario):
        pedido = reserva(
            client, cenario, [{"sector_id": cenario["plateia"], "seat_code": "B2"}]
        ).json()
        r = client.post(
            f"/orders/{pedido['id']}/pay", json=CARTAO_OK, headers=auth(client, OUTRO_CLIENTE)
        )
        assert r.status_code == 404


class TestCarteira:
    def test_so_aparecem_ingressos_pagos(self, client, cenario):
        reserva(client, cenario, [{"sector_id": cenario["plateia"], "seat_code": "A3"}])

        pago = reserva(
            client, cenario, [{"sector_id": cenario["vip"], "seat_code": "D2"}]
        ).json()
        client.post(f"/orders/{pago['id']}/pay", json=CARTAO_OK, headers=cenario["cliente"])

        ingressos = client.get("/me/tickets", headers=cenario["cliente"]).json()
        assert len(ingressos) == 1
        assert ingressos[0]["seat_code"] == "D2"
        assert ingressos[0]["movie_title"]
        assert ingressos[0]["code"]

    def test_cliente_nao_ve_ingresso_de_outro(self, client, cenario):
        pedido = reserva(
            client, cenario, [{"sector_id": cenario["plateia"], "seat_code": "A3"}]
        ).json()
        client.post(f"/orders/{pedido['id']}/pay", json=CARTAO_OK, headers=cenario["cliente"])

        assert client.get("/me/tickets", headers=auth(client, OUTRO_CLIENTE)).json() == []


class TestCancelamento:
    def test_cancelar_devolve_o_assento(self, client, cenario):
        pedido = reserva(
            client, cenario, [{"sector_id": cenario["plateia"], "seat_code": "B4"}]
        ).json()

        r = client.post(f"/orders/{pedido['id']}/cancel", headers=cenario["cliente"])
        assert r.json()["status"] == "CANCELLED"

        mapa = client.get(f"/sessions/{cenario['sessao']['id']}/seats").json()
        assert mapa["available"] == 22


class TestExpiracao:
    def test_reserva_vencida_devolve_o_assento(self, client, cenario):
        """Cliente que abandona o checkout não pode travar a poltrona."""
        from app.models.order import Order, OrderStatus
        from tests.conftest import TestSession

        pedido = reserva(
            client, cenario, [{"sector_id": cenario["plateia"], "seat_code": "C6"}]
        ).json()

        # Envelhece o pedido em vez de esperar quinze minutos.
        db = TestSession()
        try:
            registro = db.get(Order, __import__("uuid").UUID(pedido["id"]))
            registro.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            db.commit()
        finally:
            db.close()

        mapa = client.get(f"/sessions/{cenario['sessao']['id']}/seats").json()
        assert mapa["available"] == 22

        r = reserva(
            client, cenario,
            [{"sector_id": cenario["plateia"], "seat_code": "C6"}],
            headers=auth(client, OUTRO_CLIENTE),
        )
        assert r.status_code == 201

        db = TestSession()
        try:
            assert db.get(Order, __import__("uuid").UUID(pedido["id"])).status is OrderStatus.EXPIRED
        finally:
            db.close()
