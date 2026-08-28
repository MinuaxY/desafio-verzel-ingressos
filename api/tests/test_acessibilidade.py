"""Poltronas acessíveis.

Salas de espetáculo no Brasil precisam oferecer lugares acessíveis (Lei 10.098
e NBR 9050). A marcação vive no banco, e não só na interface: se fosse só
visual, o sistema não teria registro de que aquele lugar é reservado a quem
precisa dele. Ver decisão D16.
"""
import pytest

from tests.conftest import cria_conta

ORGANIZADOR = {
    "name": "Org", "email": "org@acess.dev", "password": "senhaforte123", "role": "ORGANIZER",
}

SALA_ACESSIVEL = {
    "name": "Sala Acessível",
    "location": "Centro",
    "sectors": [
        {
            "name": "Plateia",
            "rows": 6,
            "seats_per_row": 12,
            "display_order": 0,
            "special_seats": [
                {"seat_code": "A1", "kind": "WHEELCHAIR"},
                {"seat_code": "A2", "kind": "COMPANION"},
                {"seat_code": "A11", "kind": "OBESE"},
                {"seat_code": "F12", "kind": "REDUCED_MOBILITY"},
            ],
        },
    ],
}


def auth(client, dados):
    """Papel privilegiado não sai do cadastro público. Ver conftest."""
    return cria_conta(client, dados)


def cria(client, headers, sala=None):
    return client.post("/rooms", json=sala or SALA_ACESSIVEL, headers=headers)


class TestMarcacao:
    def test_grava_as_poltronas_acessiveis(self, client):
        r = cria(client, auth(client, ORGANIZADOR))
        assert r.status_code == 201

        marcadas = {s["seat_code"]: s["kind"] for s in r.json()["sectors"][0]["special_seats"]}
        assert marcadas == {
            "A1": "WHEELCHAIR",
            "A2": "COMPANION",
            "A11": "OBESE",
            "F12": "REDUCED_MOBILITY",
        }

    def test_poltrona_comum_nao_vira_registro(self, client):
        """Uma sala de 72 lugares com 4 acessíveis guarda 4 linhas, não 72."""
        r = cria(client, auth(client, ORGANIZADOR))
        setor = r.json()["sectors"][0]
        assert setor["capacity"] == 72
        assert len(setor["special_seats"]) == 4

    def test_setor_sem_marcacao_fica_vazio(self, client):
        sala = {
            **SALA_ACESSIVEL,
            "sectors": [{"name": "Plateia", "rows": 3, "seats_per_row": 5}],
        }
        r = cria(client, auth(client, ORGANIZADOR), sala)
        assert r.status_code == 201
        assert r.json()["sectors"][0]["special_seats"] == []

    def test_codigo_e_normalizado_para_maiusculas(self, client):
        sala = {
            **SALA_ACESSIVEL,
            "sectors": [
                {
                    "name": "Plateia",
                    "rows": 3,
                    "seats_per_row": 5,
                    "special_seats": [{"seat_code": " b2 ", "kind": "OBESE"}],
                }
            ],
        }
        r = cria(client, auth(client, ORGANIZADOR), sala)
        assert r.json()["sectors"][0]["special_seats"][0]["seat_code"] == "B2"


class TestValidacao:
    @pytest.mark.parametrize("codigo", ["G1", "A13", "Z9", "A0"])
    def test_poltrona_fora_da_geometria_e_recusada(self, client, codigo):
        """Marcar a G1 num setor que vai só até a fileira F criaria um lugar
        que o sistema acha que existe e a sala não tem."""
        sala = {
            **SALA_ACESSIVEL,
            "sectors": [
                {
                    "name": "Plateia",
                    "rows": 6,
                    "seats_per_row": 12,
                    "special_seats": [{"seat_code": codigo, "kind": "WHEELCHAIR"}],
                }
            ],
        }
        r = cria(client, auth(client, ORGANIZADOR), sala)
        assert r.status_code == 422
        assert codigo in r.json()["detail"]

    def test_erro_diz_qual_setor_e_quais_poltronas(self, client):
        sala = {
            **SALA_ACESSIVEL,
            "sectors": [
                {
                    "name": "Balcão",
                    "rows": 2,
                    "seats_per_row": 4,
                    "special_seats": [
                        {"seat_code": "A1", "kind": "WHEELCHAIR"},
                        {"seat_code": "D1", "kind": "OBESE"},
                    ],
                }
            ],
        }
        r = cria(client, auth(client, ORGANIZADOR), sala)
        detalhe = r.json()["detail"]
        assert "Balcão" in detalhe
        assert "D1" in detalhe
        assert "A1" not in detalhe  # A1 existe, não deve ser acusada

    def test_mesma_poltrona_marcada_duas_vezes_e_recusada(self, client):
        sala = {
            **SALA_ACESSIVEL,
            "sectors": [
                {
                    "name": "Plateia",
                    "rows": 3,
                    "seats_per_row": 5,
                    "special_seats": [
                        {"seat_code": "A1", "kind": "WHEELCHAIR"},
                        {"seat_code": "A1", "kind": "OBESE"},
                    ],
                }
            ],
        }
        assert cria(client, auth(client, ORGANIZADOR), sala).status_code == 422

    def test_tipo_inexistente_e_recusado(self, client):
        sala = {
            **SALA_ACESSIVEL,
            "sectors": [
                {
                    "name": "Plateia",
                    "rows": 3,
                    "seats_per_row": 5,
                    "special_seats": [{"seat_code": "A1", "kind": "POLTRONA_MASSAGEADORA"}],
                }
            ],
        }
        assert cria(client, auth(client, ORGANIZADOR), sala).status_code == 422


class TestVisibilidadeNaVitrine:
    def test_detalhe_publico_expoe_as_poltronas_acessiveis(self, client):
        """Quem procura sessão precisa saber onde estão os lugares acessíveis
        antes de comprar, sem precisar de conta."""
        from datetime import datetime, timedelta, timezone

        from app.catalog.fixture import FixtureProvider

        headers = auth(client, ORGANIZADOR)
        sala = cria(client, headers).json()

        quando = (datetime.now(timezone.utc) + timedelta(days=3)).replace(microsecond=0)
        sessao = client.post(
            "/organizer/sessions",
            json={
                "catalog_id": FixtureProvider().items[0].id,
                "room_id": sala["id"],
                "starts_at": quando.isoformat(),
                "prices": [{"sector_id": sala["sectors"][0]["id"], "price_cents": 3000}],
                "publish": True,
            },
            headers=headers,
        ).json()

        publico = client.get(f"/sessions/{sessao['id']}")
        assert publico.status_code == 200

        acessiveis = publico.json()["prices"][0]["sector"]["special_seats"]
        assert {s["kind"] for s in acessiveis} == {
            "WHEELCHAIR",
            "COMPANION",
            "OBESE",
            "REDUCED_MOBILITY",
        }
