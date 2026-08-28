"""Cadastro, login e autorização por papel."""
import pytest

from tests.conftest import cria_conta

CLIENTE = {
    "name": "Cliente Teste",
    "email": "cliente@teste.dev",
    "password": "senhaforte123",
}
ORGANIZADOR = {
    "name": "Organizador Teste",
    "email": "org@teste.dev",
    "password": "senhaforte123",
    "role": "ORGANIZER",
}


def registra(client, dados):
    """Cadastro público, cru — é o que estes testes exercitam."""
    return client.post("/auth/register", json=dados)


def token_de(client, dados):
    """Token de qualquer papel. Privilegiado não sai do cadastro público."""
    return cria_conta(client, dados)["Authorization"].removeprefix("Bearer ")


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
        # Exercido num endpoint real do organizador. Existia aqui uma rota
        # criada só para este teste; ela prometia sair quando os endpoints de
        # verdade passassem a valer, e tinha ficado para trás. Ver decisão D33.
        token = token_de(client, ORGANIZADOR)
        r = client.get("/organizer/sessions", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200

    def test_cliente_recebe_403_em_rota_de_organizador(self, client):
        """Autenticado, porém sem permissão: 403, não 401."""
        token = token_de(client, CLIENTE)
        r = client.get("/organizer/sessions", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403


class TestFronteiraDeConfianca:
    """O cadastro público não concede papel. Ver decisão D34.

    Antes desta correção, `role` era campo de entrada e era persistido como
    veio: bastava mandar "ORGANIZER" no corpo para receber o painel do
    organizador, e "GATE" para validar ingressos na portaria — papel que a
    própria tela de cadastro nem oferecia.
    """

    def test_pedir_papel_de_organizador_e_recusado(self, client):
        r = registra(client, {**CLIENTE, "role": "ORGANIZER"})
        assert r.status_code == 422

    def test_pedir_papel_de_portaria_e_recusado(self, client):
        r = registra(client, {**CLIENTE, "role": "GATE"})
        assert r.status_code == 422

    def test_a_recusa_e_explicita_e_nao_silenciosa(self, client):
        """422 em vez de criar um cliente calado.

        Ignorar o campo em silêncio devolveria 201 e uma conta de cliente, e
        quem pediu sairia acreditando ter recebido o que pediu.
        """
        r = registra(client, {**CLIENTE, "role": "ORGANIZER"})
        assert r.status_code == 422
        assert "role" in str(r.json()["detail"]).lower()

    def test_cadastro_limpo_cria_cliente(self, client):
        r = registra(client, CLIENTE)
        assert r.status_code == 201
        assert r.json()["user"]["role"] == "CUSTOMER"

    def test_cliente_cadastrado_nao_alcanca_o_painel(self, client):
        token = registra(client, CLIENTE).json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}
        assert client.get("/organizer/sessions", headers=h).status_code == 403
        assert client.post("/rooms", json={"name": "X", "sectors": []}, headers=h).status_code == 403

    def test_cliente_cadastrado_nao_alcanca_a_portaria(self, client):
        token = registra(client, CLIENTE).json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}
        r = client.post("/gate/validate", json={"code": "AAAABBBBCCCC.DDDDEEEEFFFF"}, headers=h)
        assert r.status_code == 403

    def test_o_fluxo_administrativo_continua_criando_papel_privilegiado(self, client):
        """A porta legítima: `python -m app.admin`, que grava direto no banco."""
        from app.admin import criar
        from app.models.user import Role

        criar("Organizadora Real", "real@admin.dev", Role.ORGANIZER, senha="senhaforte123")
        entrou = client.post(
            "/auth/login", json={"email": "real@admin.dev", "password": "senhaforte123"}
        )
        assert entrou.status_code == 200
        assert entrou.json()["user"]["role"] == "ORGANIZER"

        h = {"Authorization": f"Bearer {entrou.json()['access_token']}"}
        assert client.get("/organizer/sessions", headers=h).status_code == 200
