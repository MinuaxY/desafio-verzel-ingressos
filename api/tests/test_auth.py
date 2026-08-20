"""Cadastro, login e autorização por papel."""
import pytest

CLIENTE = {
    "name": "Cliente Teste",
    "email": "cliente@teste.dev",
    "password": "senhaforte123",
    "role": "CUSTOMER",
}
ORGANIZADOR = {
    "name": "Organizador Teste",
    "email": "org@teste.dev",
    "password": "senhaforte123",
    "role": "ORGANIZER",
}


def registra(client, dados):
    return client.post("/auth/register", json=dados)


def token_de(client, dados):
    return registra(client, dados).json()["access_token"]


class TestCadastro:
    def test_cadastro_retorna_token_e_usuario(self, client):
        r = registra(client, CLIENTE)
        assert r.status_code == 201
        corpo = r.json()
        assert corpo["token_type"] == "bearer"
        assert corpo["user"]["email"] == CLIENTE["email"]
        assert corpo["user"]["role"] == "CUSTOMER"
        assert "password" not in corpo["user"]
        assert "password_hash" not in corpo["user"]

    def test_email_duplicado_e_recusado(self, client):
        registra(client, CLIENTE)
        r = registra(client, CLIENTE)
        assert r.status_code == 409

    def test_email_normalizado_para_minusculas(self, client):
        registra(client, {**CLIENTE, "email": "MAIUSCULA@Teste.dev"})
        r = client.post(
            "/auth/login", json={"email": "maiuscula@teste.dev", "password": CLIENTE["password"]}
        )
        assert r.status_code == 200

    @pytest.mark.parametrize("senha", ["curta", "1234567"])
    def test_senha_curta_e_recusada(self, client, senha):
        r = registra(client, {**CLIENTE, "password": senha})
        assert r.status_code == 422


class TestLogin:
    def test_login_com_credencial_correta(self, client):
        registra(client, CLIENTE)
        r = client.post(
            "/auth/login", json={"email": CLIENTE["email"], "password": CLIENTE["password"]}
        )
        assert r.status_code == 200
        assert r.json()["access_token"]

    def test_senha_errada_e_recusada(self, client):
        registra(client, CLIENTE)
        r = client.post("/auth/login", json={"email": CLIENTE["email"], "password": "erradaerrada"})
        assert r.status_code == 401

    def test_usuario_inexistente_responde_igual_a_senha_errada(self, client):
        """Não entregamos a quem tenta adivinhar quais e-mails existem."""
        registra(client, CLIENTE)
        senha_errada = client.post(
            "/auth/login", json={"email": CLIENTE["email"], "password": "erradaerrada"}
        )
        inexistente = client.post(
            "/auth/login", json={"email": "ninguem@teste.dev", "password": "erradaerrada"}
        )
        assert senha_errada.status_code == inexistente.status_code == 401
        assert senha_errada.json()["detail"] == inexistente.json()["detail"]


class TestAutorizacao:
    def test_me_exige_token(self, client):
        assert client.get("/auth/me").status_code == 401

    def test_me_recusa_token_invalido(self, client):
        r = client.get("/auth/me", headers={"Authorization": "Bearer nao.e.um.token"})
        assert r.status_code == 401

    def test_me_devolve_o_usuario_do_token(self, client):
        token = token_de(client, CLIENTE)
        r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["email"] == CLIENTE["email"]

    def test_organizador_acessa_rota_de_organizador(self, client):
        token = token_de(client, ORGANIZADOR)
        r = client.get("/auth/organizer-only", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200

    def test_cliente_recebe_403_em_rota_de_organizador(self, client):
        """Autenticado, porém sem permissão: 403, não 401."""
        token = token_de(client, CLIENTE)
        r = client.get("/auth/organizer-only", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403
