"""Compra: mapa de assentos, reserva, pagamento e emissão do ingresso."""
from datetime import datetime, timedelta, timezone

import pytest

from app.catalog.factory import get_catalog_provider
from app.catalog.fixture import FixtureProvider
from app.config import get_settings
from tests.conftest import cria_conta

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


def auth(client, data):
    """Papel privilegiado não sai do cadastro público. Ver conftest."""
    return cria_conta(client, data)


@pytest.fixture
def scenario(client):
    """Uma sessão publicada, com sala de 22 lugares, pronta para comprar."""
    org = auth(client, ORGANIZADOR)
    room = client.post("/rooms", json=SALA, headers=org).json()
    starts_at = (datetime.now(timezone.utc) + timedelta(days=2)).replace(microsecond=0)

    session = client.post(
        "/organizer/sessions",
        json={
            "catalog_id": FixtureProvider().items[0].id,
            "room_id": room["id"],
            "starts_at": starts_at.isoformat(),
            "prices": [
                {"sector_id": s["id"], "price_cents": 3000 if s["name"] == "Plateia" else 5000}
                for s in room["sectors"]
            ],
            "publish": True,
        },
        headers=org,
    ).json()

    sectors = {s["name"]: s["id"] for s in room["sectors"]}
    return {
        "org": org,
        "sala": room,
        "sessao": session,
        "plateia": sectors["Plateia"],
        "vip": sectors["VIP"],
        "cliente": auth(client, CLIENTE),
    }


def hold(client, scenario, seats, headers=None):
    return client.post(
        "/orders",
        json={"session_id": scenario["sessao"]["id"], "seats": seats},
        headers=headers or scenario["cliente"],
    )


class TestMapaDeAssentos:
    def test_mapa_e_publico(self, client, scenario):
        r = client.get(f"/sessions/{scenario['sessao']['id']}/seats")
        assert r.status_code == 200

    def test_mapa_traz_a_geometria_completa(self, client, scenario):
        corpo = client.get(f"/sessions/{scenario['sessao']['id']}/seats").json()
        assert corpo["capacity"] == 22
        assert corpo["available"] == 22

        plateia = corpo["sectors"][0]
        assert plateia["name"] == "Plateia"
        assert len(plateia["seats"]) == 18
        assert plateia["seats"][0]["code"] == "A1"
        assert plateia["seats"][-1]["code"] == "C6"

    def test_mapa_marca_as_poltronas_acessiveis(self, client, scenario):
        plateia = client.get(f"/sessions/{scenario['sessao']['id']}/seats").json()["sectors"][0]
        tipos = {s["code"]: s["kind"] for s in plateia["seats"] if s["kind"]}
        assert tipos == {"A1": "WHEELCHAIR", "A2": "COMPANION"}

    def test_assento_reservado_aparece_ocupado(self, client, scenario):
        hold(client, scenario, [{"sector_id": scenario["plateia"], "seat_code": "B3"}])

        corpo = client.get(f"/sessions/{scenario['sessao']['id']}/seats").json()
        assert corpo["available"] == 21
        b3 = next(s for s in corpo["sectors"][0]["seats"] if s["code"] == "B3")
        assert b3["taken"] is True

    def test_preco_por_setor_aparece_no_mapa(self, client, scenario):
        sectors = client.get(f"/sessions/{scenario['sessao']['id']}/seats").json()["sectors"]
        assert {s["name"]: s["price_cents"] for s in sectors} == {"Plateia": 3000, "VIP": 5000}


class TestReserva:
    def test_exige_autenticacao(self, client, scenario):
        r = client.post(
            "/orders",
            json={"session_id": scenario["sessao"]["id"], "seats": [
                {"sector_id": scenario["plateia"], "seat_code": "A3"}
            ]},
        )
        assert r.status_code == 401

    def test_organizador_nao_compra(self, client, scenario):
        r = hold(
            client, scenario,
            [{"sector_id": scenario["plateia"], "seat_code": "A3"}],
            headers=scenario["org"],
        )
        assert r.status_code == 403

    def test_reserva_nasce_pendente(self, client, scenario):
        r = hold(client, scenario, [{"sector_id": scenario["plateia"], "seat_code": "A3"}])
        assert r.status_code == 201
        assert r.json()["status"] == "PENDING"
        assert r.json()["tickets"][0]["status"] == "RESERVED"

    def test_total_soma_os_setores(self, client, scenario):
        # A Plateia ocupa A a C, entao o VIP comeca em D: as fileiras sao
        # continuas na sala, nao reiniciadas por setor. Ver decisao D23.
        r = hold(client, scenario, [
            {"sector_id": scenario["plateia"], "seat_code": "A3"},
            {"sector_id": scenario["vip"], "seat_code": "D1"},
        ])
        assert r.json()["total_cents"] == 8000

    def test_reserva_pendente_nao_tem_codigo(self, client, scenario):
        """Sem pagamento não há ingresso, e sem ingresso não há QR."""
        r = hold(client, scenario, [{"sector_id": scenario["plateia"], "seat_code": "A3"}])
        assert r.json()["tickets"][0]["code"] is None

    def test_assento_ja_ocupado_e_recusado(self, client, scenario):
        hold(client, scenario, [{"sector_id": scenario["plateia"], "seat_code": "B1"}])
        r = hold(
            client, scenario,
            [{"sector_id": scenario["plateia"], "seat_code": "B1"}],
            headers=auth(client, OUTRO_CLIENTE),
        )
        assert r.status_code == 409
        assert "B1" in r.json()["detail"]

    @pytest.mark.parametrize("code", ["D1", "A7", "Z9"])
    def test_assento_inexistente_e_recusado(self, client, scenario, code):
        r = hold(client, scenario, [{"sector_id": scenario["plateia"], "seat_code": code}])
        assert r.status_code == 422

    def test_mesmo_assento_duas_vezes_no_pedido_e_recusado(self, client, scenario):
        r = hold(client, scenario, [
            {"sector_id": scenario["plateia"], "seat_code": "A3"},
            {"sector_id": scenario["plateia"], "seat_code": "A3"},
        ])
        assert r.status_code == 422

    def test_limite_de_assentos_por_compra(self, client, scenario):
        muitos = [
            {"sector_id": scenario["plateia"], "seat_code": f"A{i}"} for i in range(1, 7)
        ] * 2
        r = hold(client, scenario, muitos)
        assert r.status_code == 422


class TestPagamento:
    def test_aprovado_emite_ingresso_com_codigo(self, client, scenario):
        order = hold(
            client, scenario, [{"sector_id": scenario["plateia"], "seat_code": "A3"}]
        ).json()

        r = client.post(
            f"/orders/{order['id']}/pay", json=CARTAO_OK, headers=scenario["cliente"]
        )
        assert r.status_code == 200
        corpo = r.json()
        assert corpo["status"] == "PAID"
        assert corpo["paid_at"] is not None

        ticket = corpo["tickets"][0]
        assert ticket["status"] == "VALID"
        assert ticket["code"] and "." in ticket["code"]
        assert ticket["share_token"]

    @pytest.mark.parametrize(
        "card,excerpt", [(CARTAO_RECUSA, "recusado"), (CARTAO_SEM_SALDO, "Saldo")]
    )
    def test_recusado_nao_emite_ingresso(self, client, scenario, card, excerpt):
        order = hold(
            client, scenario, [{"sector_id": scenario["plateia"], "seat_code": "A4"}]
        ).json()

        corpo = client.post(
            f"/orders/{order['id']}/pay", json=card, headers=scenario["cliente"]
        ).json()

        assert corpo["status"] == "DECLINED"
        assert excerpt in corpo["decline_reason"]
        assert corpo["tickets"][0]["status"] == "CANCELLED"
        assert corpo["tickets"][0]["code"] is None

    def test_recusa_devolve_o_assento_ao_estoque(self, client, scenario):
        """O índice único parcial ignora CANCELLED, então a poltrona volta a
        ficar livre sem nenhuma limpeza."""
        order = hold(
            client, scenario, [{"sector_id": scenario["plateia"], "seat_code": "C1"}]
        ).json()
        client.post(f"/orders/{order['id']}/pay", json=CARTAO_RECUSA, headers=scenario["cliente"])

        mapa = client.get(f"/sessions/{scenario['sessao']['id']}/seats").json()
        c1 = next(s for s in mapa["sectors"][0]["seats"] if s["code"] == "C1")
        assert c1["taken"] is False

        # E outra pessoa consegue comprar a mesma poltrona.
        r = hold(
            client, scenario,
            [{"sector_id": scenario["plateia"], "seat_code": "C1"}],
            headers=auth(client, OUTRO_CLIENTE),
        )
        assert r.status_code == 201

    def test_cartao_invalido_e_recusado(self, client, scenario):
        order = hold(
            client, scenario, [{"sector_id": scenario["plateia"], "seat_code": "A5"}]
        ).json()
        r = client.post(
            f"/orders/{order['id']}/pay",
            json={"card_number": "123", "card_holder": "X Y"},
            headers=scenario["cliente"],
        )
        assert r.status_code == 422  # nem chega ao serviço: falha na validação de entrada

    def test_nao_paga_duas_vezes(self, client, scenario):
        order = hold(
            client, scenario, [{"sector_id": scenario["plateia"], "seat_code": "A6"}]
        ).json()
        client.post(f"/orders/{order['id']}/pay", json=CARTAO_OK, headers=scenario["cliente"])

        r = client.post(
            f"/orders/{order['id']}/pay", json=CARTAO_OK, headers=scenario["cliente"]
        )
        assert r.status_code == 409

    def test_pedido_de_outro_cliente_responde_404(self, client, scenario):
        order = hold(
            client, scenario, [{"sector_id": scenario["plateia"], "seat_code": "B2"}]
        ).json()
        r = client.post(
            f"/orders/{order['id']}/pay", json=CARTAO_OK, headers=auth(client, OUTRO_CLIENTE)
        )
        assert r.status_code == 404


class TestCarteira:
    def test_so_aparecem_ingressos_pagos(self, client, scenario):
        hold(client, scenario, [{"sector_id": scenario["plateia"], "seat_code": "A3"}])

        pago = hold(
            client, scenario, [{"sector_id": scenario["vip"], "seat_code": "D2"}]
        ).json()
        client.post(f"/orders/{pago['id']}/pay", json=CARTAO_OK, headers=scenario["cliente"])

        ingressos = client.get("/me/tickets", headers=scenario["cliente"]).json()
        assert len(ingressos) == 1
        assert ingressos[0]["seat_code"] == "D2"
        assert ingressos[0]["movie_title"]
        assert ingressos[0]["code"]

    def test_cliente_nao_ve_ingresso_de_outro(self, client, scenario):
        order = hold(
            client, scenario, [{"sector_id": scenario["plateia"], "seat_code": "A3"}]
        ).json()
        client.post(f"/orders/{order['id']}/pay", json=CARTAO_OK, headers=scenario["cliente"])

        assert client.get("/me/tickets", headers=auth(client, OUTRO_CLIENTE)).json() == []


class TestCancelamento:
    def test_cancelar_devolve_o_assento(self, client, scenario):
        order = hold(
            client, scenario, [{"sector_id": scenario["plateia"], "seat_code": "B4"}]
        ).json()

        r = client.post(f"/orders/{order['id']}/cancel", headers=scenario["cliente"])
        assert r.json()["status"] == "CANCELLED"

        mapa = client.get(f"/sessions/{scenario['sessao']['id']}/seats").json()
        assert mapa["available"] == 22


class TestExpiracao:
    def test_reserva_vencida_devolve_o_assento(self, client, scenario):
        """Cliente que abandona o checkout não pode travar a poltrona."""
        from app.models.order import Order, OrderStatus
        from tests.conftest import TestSession

        order = hold(
            client, scenario, [{"sector_id": scenario["plateia"], "seat_code": "C6"}]
        ).json()

        # Envelhece o pedido em vez de esperar quinze minutos.
        db = TestSession()
        try:
            registro = db.get(Order, __import__("uuid").UUID(order["id"]))
            registro.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            db.commit()
        finally:
            db.close()

        mapa = client.get(f"/sessions/{scenario['sessao']['id']}/seats").json()
        assert mapa["available"] == 22

        r = hold(
            client, scenario,
            [{"sector_id": scenario["plateia"], "seat_code": "C6"}],
            headers=auth(client, OUTRO_CLIENTE),
        )
        assert r.status_code == 201

        db = TestSession()
        try:
            gravado = db.get(Order, __import__("uuid").UUID(order["id"]))
            assert gravado.status is OrderStatus.EXPIRED
        finally:
            db.close()
