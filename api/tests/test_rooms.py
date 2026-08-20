"""Salas e setores."""
import pytest

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


def auth(client, dados):
    token = client.post("/auth/register", json=dados).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestAutorizacao:
    def test_sem_token_e_recusado(self, client):
        assert client.get("/rooms").status_code == 401

    def test_cliente_nao_gerencia_salas(self, client):
        assert client.get("/rooms", headers=auth(client, CLIENTE)).status_code == 403


class TestCriacao:
    def test_cria_sala_com_setores(self, client):
        r = client.post("/rooms", json=SALA, headers=auth(client, ORGANIZADOR))
        assert r.status_code == 201
        sala = r.json()
        assert sala["name"] == "Sala 1"
        assert len(sala["sectors"]) == 2

    def test_capacidade_e_soma_dos_setores(self, client):
        """5x10 na plateia mais 2x6 no VIP dá 62."""
        r = client.post("/rooms", json=SALA, headers=auth(client, ORGANIZADOR))
        assert r.json()["capacity"] == 62

    def test_capacidade_por_setor(self, client):
        r = client.post("/rooms", json=SALA, headers=auth(client, ORGANIZADOR))
        setores = {s["name"]: s["capacity"] for s in r.json()["sectors"]}
        assert setores == {"Plateia": 50, "VIP": 12}

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
        "setor",
        [
            {"name": "X", "rows": 0, "seats_per_row": 5},
            {"name": "X", "rows": 99, "seats_per_row": 5},
            {"name": "X", "rows": 5, "seats_per_row": 0},
            {"name": "X", "rows": 5, "seats_per_row": 999},
        ],
    )
    def test_geometria_absurda_e_recusada(self, client, setor):
        r = client.post(
            "/rooms", json={**SALA, "sectors": [setor]}, headers=auth(client, ORGANIZADOR)
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


class TestDesativacao:
    def test_desativar_remove_da_listagem(self, client):
        headers = auth(client, ORGANIZADOR)
        criada = client.post("/rooms", json=SALA, headers=headers).json()

        r = client.delete(f"/rooms/{criada['id']}", headers=headers)
        assert r.status_code == 200
        assert r.json()["active"] is False
        assert client.get("/rooms", headers=headers).json() == []

    def test_sala_desativada_continua_acessivel_por_id(self, client):
        """A sala não é apagada: sessões passadas apontam para ela."""
        headers = auth(client, ORGANIZADOR)
        criada = client.post("/rooms", json=SALA, headers=headers).json()
        client.delete(f"/rooms/{criada['id']}", headers=headers)
        assert client.get(f"/rooms/{criada['id']}", headers=headers).status_code == 200
