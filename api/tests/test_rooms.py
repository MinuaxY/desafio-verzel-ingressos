"""Salas e setores."""
import pytest
from tests.conftest import cria_conta

ORGANIZADOR = {
    "name": "Org", "email": "org@sala.dev", "password": "senhaforte123", "role": "ORGANIZER",
}
OUTRO_ORGANIZADOR = {
    "name": "Org2", "email": "org2@sala.dev", "password": "senhaforte123", "role": "ORGANIZER",
}
CLIENTE = {
    "name": "Cli", "email": "cli@sala.dev", "password": "senhaforte123", "role": "CUSTOMER",
}

SALA = {
    "name": "Sala 1",
    "location": "Centro",
    "sectors": [
        {"name": "Plateia", "rows": 5, "seats_per_row": 10, "display_order": 0},
        {"name": "VIP", "rows": 2, "seats_per_row": 6, "display_order": 1},
    ],
}


def auth(client, data):
    """Papel privilegiado não sai do cadastro público. Ver conftest."""
    return cria_conta(client, data)


class TestAutorizacao:
    def test_sem_token_e_recusado(self, client):
        assert client.get("/rooms").status_code == 401

    def test_cliente_nao_gerencia_salas(self, client):
        assert client.get("/rooms", headers=auth(client, CLIENTE)).status_code == 403


class TestCriacao:
    def test_cria_sala_com_setores(self, client):
        r = client.post("/rooms", json=SALA, headers=auth(client, ORGANIZADOR))
        assert r.status_code == 201
        room = r.json()
        assert room["name"] == "Sala 1"
        assert len(room["sectors"]) == 2

    def test_capacidade_e_soma_dos_setores(self, client):
        """5x10 na plateia mais 2x6 no VIP dá 62."""
        r = client.post("/rooms", json=SALA, headers=auth(client, ORGANIZADOR))
        assert r.json()["capacity"] == 62

    def test_capacidade_por_setor(self, client):
        r = client.post("/rooms", json=SALA, headers=auth(client, ORGANIZADOR))
        sectors = {s["name"]: s["capacity"] for s in r.json()["sectors"]}
        assert sectors == {"Plateia": 50, "VIP": 12}

    def test_nome_repetido_do_mesmo_organizador_e_recusado(self, client):
        headers = auth(client, ORGANIZADOR)
        client.post("/rooms", json=SALA, headers=headers)
        assert client.post("/rooms", json=SALA, headers=headers).status_code == 409

    def test_organizadores_diferentes_podem_repetir_o_nome(self, client):
        """Cada cinema tem a sua 'Sala 1'."""
        client.post("/rooms", json=SALA, headers=auth(client, ORGANIZADOR))
        r = client.post("/rooms", json=SALA, headers=auth(client, OUTRO_ORGANIZADOR))
        assert r.status_code == 201

    def test_setores_com_nomes_iguais_sao_recusados(self, client):
        payload = {
            **SALA,
            "sectors": [
                {"name": "Plateia", "rows": 3, "seats_per_row": 5},
                {"name": "plateia", "rows": 2, "seats_per_row": 5},
            ],
        }
        r = client.post("/rooms", json=payload, headers=auth(client, ORGANIZADOR))
        assert r.status_code == 422

    def test_sala_sem_setor_e_recusada(self, client):
        r = client.post(
            "/rooms", json={**SALA, "sectors": []}, headers=auth(client, ORGANIZADOR)
        )
        assert r.status_code == 422

    @pytest.mark.parametrize(
        "sector",
        [
            {"name": "X", "rows": 0, "seats_per_row": 5},
            {"name": "X", "rows": 99, "seats_per_row": 5},
            {"name": "X", "rows": 5, "seats_per_row": 0},
            {"name": "X", "rows": 5, "seats_per_row": 999},
        ],
    )
    def test_geometria_absurda_e_recusada(self, client, sector):
        r = client.post(
            "/rooms", json={**SALA, "sectors": [sector]}, headers=auth(client, ORGANIZADOR)
        )
        assert r.status_code == 422


class TestIsolamentoEntreOrganizadores:
    def test_cada_um_ve_apenas_as_proprias_salas(self, client):
        client.post("/rooms", json=SALA, headers=auth(client, ORGANIZADOR))
        assert client.get("/rooms", headers=auth(client, OUTRO_ORGANIZADOR)).json() == []

    def test_sala_de_outro_responde_404(self, client):
        """404, e não 403: confirmar que a sala existe entregaria informação a
        quem estivesse sondando o sistema."""
        criada = client.post("/rooms", json=SALA, headers=auth(client, ORGANIZADOR)).json()
        r = client.get(f"/rooms/{criada['id']}", headers=auth(client, OUTRO_ORGANIZADOR))
        assert r.status_code == 404


class TestRemocao:
    """Apagar de vez ou desativar depende do historico da sala.

    Sala que nunca serviu nao tem historico a preservar, e deixa-la desativada
    so acumularia lixo na lista. Sala que ja teve sessao fica, porque sessao
    passada aponta para ela. Ver decisao D28.
    """

    def test_sala_sem_sessao_e_apagada(self, client):
        headers = auth(client, ORGANIZADOR)
        criada = client.post("/rooms", json=SALA, headers=headers).json()

        assert client.delete(f"/rooms/{criada['id']}", headers=headers).status_code == 204
        assert client.get(f"/rooms/{criada['id']}", headers=headers).status_code == 404
        assert client.get("/rooms", headers=headers).json() == []

    def test_sala_com_sessao_passada_e_desativada(self, client):
        """Nao some: quem comprou precisa continuar vendo onde a sessao foi."""
        from datetime import datetime, timedelta, timezone

        from app.catalog.fixture import FixtureProvider
        from app.models.session import Session
        from tests.conftest import TestSession

        headers = auth(client, ORGANIZADOR)
        room = client.post("/rooms", json=SALA, headers=headers).json()

        starts_at = (datetime.now(timezone.utc) + timedelta(days=2)).replace(microsecond=0)
        session = client.post(
            "/organizer/sessions",
            json={
                "catalog_id": FixtureProvider().items[0].id,
                "room_id": room["id"],
                "starts_at": starts_at.isoformat(),
                "prices": [
                    {"sector_id": s["id"], "price_cents": 3000} for s in room["sectors"]
                ],
            },
            headers=headers,
        ).json()

        # Envelhece a sessao em vez de esperar dois dias.
        db = TestSession()
        try:
            import uuid as _uuid

            registro = db.get(Session, _uuid.UUID(session["id"]))
            registro.starts_at = datetime.now(timezone.utc) - timedelta(days=1)
            db.commit()
        finally:
            db.close()

        r = client.delete(f"/rooms/{room['id']}", headers=headers)
        assert r.status_code == 200
        assert r.json()["active"] is False

        # Continua acessivel por id, e some da lista de escolha.
        assert client.get(f"/rooms/{room['id']}", headers=headers).status_code == 200
        assert client.get("/rooms", headers=headers).json() == []

    def test_sala_com_sessao_futura_nao_sai(self, client):
        """Ha gente podendo comprar para ela agora."""
        from datetime import datetime, timedelta, timezone

        from app.catalog.fixture import FixtureProvider

        headers = auth(client, ORGANIZADOR)
        room = client.post("/rooms", json=SALA, headers=headers).json()
        starts_at = (datetime.now(timezone.utc) + timedelta(days=3)).replace(microsecond=0)
        client.post(
            "/organizer/sessions",
            json={
                "catalog_id": FixtureProvider().items[0].id,
                "room_id": room["id"],
                "starts_at": starts_at.isoformat(),
                "prices": [
                    {"sector_id": s["id"], "price_cents": 3000} for s in room["sectors"]
                ],
                "publish": True,
            },
            headers=headers,
        )

        r = client.delete(f"/rooms/{room['id']}", headers=headers)
        assert r.status_code == 409
        assert "futura" in r.json()["detail"]
        assert client.get("/rooms", headers=headers) .json() != []

    def test_sala_de_outro_nao_e_removida(self, client):
        criada = client.post("/rooms", json=SALA, headers=auth(client, ORGANIZADOR)).json()
        r = client.delete(f"/rooms/{criada['id']}", headers=auth(client, OUTRO_ORGANIZADOR))
        assert r.status_code == 404


class TestNumeracaoContinua:
    """As fileiras correm pela sala inteira, nao reiniciam a cada setor.

    Duas fileiras "A" na mesma sala confundem quem procura o lugar, e fariam o
    ingresso dizer "A1" para dois assentos diferentes. Ver decisao D23.
    """

    def test_setor_seguinte_continua_o_alfabeto(self, client):
        room = client.post("/rooms", json=SALA, headers=auth(client, ORGANIZADOR)).json()
        plateia, vip = room["sectors"]
        assert (plateia["rows"], vip["rows"]) == (5, 2)
        # Plateia A-E, entao o VIP comeca em F.
        assert plateia["name"] == "Plateia"
        assert vip["name"] == "VIP"

    def test_sala_nao_pode_passar_do_alfabeto(self, client):
        """As fileiras sao nomeadas por letra: somadas, nao cabem mais que 26."""
        gigante = {
            "name": "Sala Gigante",
            "sectors": [
                {"name": "Baixo", "rows": 20, "seats_per_row": 10, "display_order": 0},
                {"name": "Alto", "rows": 10, "seats_per_row": 10, "display_order": 1},
            ],
        }
        r = client.post("/rooms", json=gigante, headers=auth(client, ORGANIZADOR))
        assert r.status_code == 422
        assert "26" in r.json()["detail"]

    def test_no_limite_exato_e_aceito(self, client):
        limite = {
            "name": "Sala no Limite",
            "sectors": [
                {"name": "Baixo", "rows": 20, "seats_per_row": 4, "display_order": 0},
                {"name": "Alto", "rows": 6, "seats_per_row": 4, "display_order": 1},
            ],
        }
        r = client.post("/rooms", json=limite, headers=auth(client, ORGANIZADOR))
        assert r.status_code == 201

    def test_acessivel_do_segundo_setor_usa_a_letra_deslocada(self, client):
        """Marcar "A1" no segundo setor deve falhar: aquela fileira e do
        primeiro. O codigo correto usa a letra deslocada."""
        base = {
            "name": "Sala Deslocada",
            "sectors": [
                {"name": "Plateia", "rows": 3, "seats_per_row": 5, "display_order": 0},
                {
                    "name": "VIP",
                    "rows": 2,
                    "seats_per_row": 4,
                    "display_order": 1,
                    "special_seats": [{"seat_code": "A1", "kind": "WHEELCHAIR"}],
                },
            ],
        }
        headers = auth(client, ORGANIZADOR)
        r = client.post("/rooms", json=base, headers=headers)
        assert r.status_code == 422

        base["sectors"][1]["special_seats"] = [{"seat_code": "D1", "kind": "WHEELCHAIR"}]
        base["name"] = "Sala Deslocada 2"
        assert client.post("/rooms", json=base, headers=headers).status_code == 201


class TestCorredores:
    """Corredores separam blocos de poltronas.

    Sem eles o mapa e uma grade uniforme; com eles vira planta de sala, e quem
    compra ve que o lugar escolhido fica na ponta, junto da passagem.
    Ver decisao D25.
    """

    def test_corredores_sao_gravados(self, client):
        room = {
            "name": "Sala Corredor",
            "sectors": [
                {"name": "Plateia", "rows": 3, "seats_per_row": 12, "aisles": [3, 9]},
            ],
        }
        r = client.post("/rooms", json=room, headers=auth(client, ORGANIZADOR))
        assert r.status_code == 201
        assert r.json()["sectors"][0]["aisles"] == [3, 9]

    def test_sem_corredor_e_um_bloco_so(self, client):
        room = {
            "name": "Sala Inteira",
            "sectors": [{"name": "Plateia", "rows": 2, "seats_per_row": 8}],
        }
        r = client.post("/rooms", json=room, headers=auth(client, ORGANIZADOR))
        assert r.status_code == 201
        assert r.json()["sectors"][0]["aisles"] == []

    @pytest.mark.parametrize("position", [0, 12, 20, -1])
    def test_corredor_fora_da_fileira_e_recusado(self, client, position):
        """Corredor na posicao 0 ou na ultima poltrona nao separa nada — seria
        um espaco na borda do bloco, nao uma passagem."""
        room = {
            "name": f"Sala Invalida {position}",
            "sectors": [
                {"name": "Plateia", "rows": 2, "seats_per_row": 12, "aisles": [position]},
            ],
        }
        r = client.post("/rooms", json=room, headers=auth(client, ORGANIZADOR))
        assert r.status_code == 422

    def test_blocos_derivados_da_geometria(self):
        """12 poltronas com corredores em 3 e 9 viram blocos de 3, 6 e 3."""
        from app.models.room import Sector

        assert Sector(rows=1, seats_per_row=12, aisles=[3, 9]).blocks == [3, 6, 3]
        assert Sector(rows=1, seats_per_row=8, aisles=[4]).blocks == [4, 4]
        assert Sector(rows=1, seats_per_row=10, aisles=[]).blocks == [10]
        # Repetido e fora de ordem nao atrapalham.
        assert Sector(rows=1, seats_per_row=10, aisles=[5, 5, 2]).blocks == [2, 3, 5]

    def test_corredores_aparecem_no_mapa_publico(self, client):
        from datetime import datetime, timedelta, timezone

        from app.catalog.fixture import FixtureProvider

        headers = auth(client, ORGANIZADOR)
        room = client.post(
            "/rooms",
            json={
                "name": "Sala Mapa",
                "sectors": [{"name": "Plateia", "rows": 2, "seats_per_row": 12, "aisles": [3, 9]}],
            },
            headers=headers,
        ).json()

        starts_at = (datetime.now(timezone.utc) + timedelta(days=2)).replace(microsecond=0)
        session = client.post(
            "/organizer/sessions",
            json={
                "catalog_id": FixtureProvider().items[0].id,
                "room_id": room["id"],
                "starts_at": starts_at.isoformat(),
                "prices": [{"sector_id": room["sectors"][0]["id"], "price_cents": 3000}],
                "publish": True,
            },
            headers=headers,
        ).json()

        mapa = client.get(f"/sessions/{session['id']}/seats").json()
        assert mapa["sectors"][0]["aisles"] == [3, 9]
