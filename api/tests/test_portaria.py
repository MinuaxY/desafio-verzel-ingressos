"""Portaria: validação do ingresso na entrada, e link compartilhado."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.catalog.factory import get_catalog_provider
from app.catalog.fixture import FixtureProvider
from app.config import get_settings
from app.core import ticket_code

ORGANIZADOR = {
    "name": "Org", "email": "org@gate.dev", "password": "senhaforte123", "role": "ORGANIZER",
}
CLIENTE = {
    "name": "Cli", "email": "cli@gate.dev", "password": "senhaforte123", "role": "CUSTOMER",
}
PORTEIRO = {
    "name": "Gate", "email": "gate@gate.dev", "password": "senhaforte123", "role": "GATE",
}
CARTAO_OK = {"card_number": "4111111111111111", "card_holder": "PAULO V"}

SALA = {
    "name": "Sala Portaria",
    "sectors": [{"name": "Plateia", "rows": 2, "seats_per_row": 5}],
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


def cria_sessao(client, org, nome_sala, dias=2):
    sala = client.post("/rooms", json={**SALA, "name": nome_sala}, headers=org).json()
    quando = (datetime.now(timezone.utc) + timedelta(days=dias)).replace(microsecond=0)
    sessao = client.post(
        "/organizer/sessions",
        json={
            "catalog_id": FixtureProvider().items[0].id,
            "room_id": sala["id"],
            "starts_at": quando.isoformat(),
            "prices": [{"sector_id": sala["sectors"][0]["id"], "price_cents": 3000}],
            "publish": True,
        },
        headers=org,
    ).json()
    return sala, sessao


@pytest.fixture
def ingresso_pago(client):
    """Um ingresso comprado e pago, pronto para ser validado."""
    org = auth(client, ORGANIZADOR)
    cliente = auth(client, CLIENTE)
    sala, sessao = cria_sessao(client, org, "Sala Portaria")

    pedido = client.post(
        "/orders",
        json={
            "session_id": sessao["id"],
            "seats": [{"sector_id": sala["sectors"][0]["id"], "seat_code": "A1"}],
        },
        headers=cliente,
    ).json()

    pago = client.post(f"/orders/{pedido['id']}/pay", json=CARTAO_OK, headers=cliente).json()

    return {
        "org": org,
        "cliente": cliente,
        "porteiro": auth(client, PORTEIRO),
        "sala": sala,
        "sessao": sessao,
        "ticket": pago["tickets"][0],
        "codigo": pago["tickets"][0]["code"],
    }


class TestAutorizacao:
    def test_sem_token_e_recusado(self, client, ingresso_pago):
        r = client.post("/gate/validate", json={"code": ingresso_pago["codigo"]})
        assert r.status_code == 401

    def test_cliente_nao_valida_ingresso(self, client, ingresso_pago):
        """Quem compra não pode dar baixa no próprio ingresso."""
        r = client.post(
            "/gate/validate",
            json={"code": ingresso_pago["codigo"]},
            headers=ingresso_pago["cliente"],
        )
        assert r.status_code == 403

    def test_organizador_nao_valida_ingresso(self, client, ingresso_pago):
        r = client.post(
            "/gate/validate",
            json={"code": ingresso_pago["codigo"]},
            headers=ingresso_pago["org"],
        )
        assert r.status_code == 403


class TestQuatroRespostas:
    """As quatro respostas que o enunciado pede."""

    def test_valido(self, client, ingresso_pago):
        r = client.post(
            "/gate/validate",
            json={"code": ingresso_pago["codigo"]},
            headers=ingresso_pago["porteiro"],
        )
        assert r.status_code == 200
        corpo = r.json()
        assert corpo["result"] == "VALID"
        assert corpo["ticket"]["seat_code"] == "A1"
        assert corpo["used_at"]

    def test_ja_utilizado(self, client, ingresso_pago):
        headers = ingresso_pago["porteiro"]
        client.post("/gate/validate", json={"code": ingresso_pago["codigo"]}, headers=headers)

        r = client.post(
            "/gate/validate", json={"code": ingresso_pago["codigo"]}, headers=headers
        )
        assert r.json()["result"] == "ALREADY_USED"

    def test_invalido(self, client, ingresso_pago):
        r = client.post(
            "/gate/validate",
            json={"code": "AAAABBBBCCCC.DDDDEEEEFFFF"},
            headers=ingresso_pago["porteiro"],
        )
        assert r.json()["result"] == "INVALID"

    def test_sessao_errada(self, client, ingresso_pago):
        _, outra = cria_sessao(client, ingresso_pago["org"], "Sala Outra", dias=4)

        r = client.post(
            "/gate/validate",
            json={"code": ingresso_pago["codigo"], "session_id": outra["id"]},
            headers=ingresso_pago["porteiro"],
        )
        assert r.json()["result"] == "WRONG_SESSION"

    def test_sessao_certa_passa(self, client, ingresso_pago):
        r = client.post(
            "/gate/validate",
            json={"code": ingresso_pago["codigo"], "session_id": ingresso_pago["sessao"]["id"]},
            headers=ingresso_pago["porteiro"],
        )
        assert r.json()["result"] == "VALID"

    def test_sessao_errada_tem_prioridade_sobre_ja_usado(self, client, ingresso_pago):
        """Quem entrou legitimamente numa sala e apareceu na porta errada
        precisa ouvir 'sessão errada', não 'já utilizado'."""
        headers = ingresso_pago["porteiro"]
        client.post("/gate/validate", json={"code": ingresso_pago["codigo"]}, headers=headers)

        _, outra = cria_sessao(client, ingresso_pago["org"], "Sala Terceira", dias=5)
        r = client.post(
            "/gate/validate",
            json={"code": ingresso_pago["codigo"], "session_id": outra["id"]},
            headers=headers,
        )
        assert r.json()["result"] == "WRONG_SESSION"


class TestCodigoNaoForjavel:
    def test_id_valido_com_assinatura_errada_e_recusado(self, client, ingresso_pago):
        """Sem o segredo do servidor não dá para produzir um código aceito."""
        parte_id = ingresso_pago["codigo"].split(".")[0]
        r = client.post(
            "/gate/validate",
            json={"code": f"{parte_id}.AAAAAAAAAAAAAAAAAAAA"},
            headers=ingresso_pago["porteiro"],
        )
        assert r.json()["result"] == "INVALID"

    def test_codigo_sem_assinatura_e_recusado(self, client, ingresso_pago):
        parte_id = ingresso_pago["codigo"].split(".")[0]
        r = client.post(
            "/gate/validate", json={"code": parte_id}, headers=ingresso_pago["porteiro"]
        )
        assert r.json()["result"] == "INVALID"

    def test_ingresso_inexistente_com_assinatura_valida(self, client, ingresso_pago):
        """Assinatura correta de um id que não existe: a assinatura passa, o
        banco reprova. É por isso que as duas conferências são necessárias."""
        codigo = ticket_code.gerar(uuid.uuid4())
        r = client.post(
            "/gate/validate", json={"code": codigo}, headers=ingresso_pago["porteiro"]
        )
        assert r.json()["result"] == "INVALID"

    def test_ingresso_nao_pago_nao_entra(self, client, ingresso_pago):
        cliente = ingresso_pago["cliente"]
        pedido = client.post(
            "/orders",
            json={
                "session_id": ingresso_pago["sessao"]["id"],
                "seats": [
                    {"sector_id": ingresso_pago["sala"]["sectors"][0]["id"], "seat_code": "A2"}
                ],
            },
            headers=cliente,
        ).json()

        codigo = ticket_code.gerar(uuid.UUID(pedido["tickets"][0]["id"]))
        r = client.post(
            "/gate/validate", json={"code": codigo}, headers=ingresso_pago["porteiro"]
        )
        assert r.json()["result"] == "INVALID"
        assert "não pago" in r.json()["message"]


class TestToleranciaNaDigitacao:
    """A portaria digita o código quando a câmera falha, olhando para um papel."""

    @pytest.mark.parametrize("transforma", [
        lambda c: c.lower(),
        lambda c: f"  {c}  ",
        lambda c: c.replace(".", " ."),
    ])
    def test_aceita_variacoes_de_digitacao(self, client, ingresso_pago, transforma):
        r = client.post(
            "/gate/validate",
            json={"code": transforma(ingresso_pago["codigo"])},
            headers=ingresso_pago["porteiro"],
        )
        assert r.json()["result"] == "VALID"


class TestLinkCompartilhado:
    def test_abre_sem_conta(self, client, ingresso_pago):
        token = ingresso_pago["ticket"]["share_token"]
        r = client.get(f"/shared/{token}")
        assert r.status_code == 200
        assert r.json()["seat_code"] == "A1"
        assert r.json()["movie_title"]

    def test_link_traz_o_codigo_para_quem_recebeu_poder_entrar(self, client, ingresso_pago):
        """Comprar três lugares e mandar um para cada amigo é o caso de uso:
        um link que não deixasse a pessoa passar na portaria não serviria."""
        token = ingresso_pago["ticket"]["share_token"]
        assert client.get(f"/shared/{token}").json()["code"] == ingresso_pago["codigo"]

    def test_token_inexistente_responde_404(self, client, ingresso_pago):
        assert client.get(f"/shared/{uuid.uuid4()}").status_code == 404


class TestCodigoIsolado:
    def test_ida_e_volta(self):
        tid = uuid.uuid4()
        assert ticket_code.conferir(ticket_code.gerar(tid)) == tid

    def test_ids_diferentes_geram_codigos_diferentes(self):
        assert ticket_code.gerar(uuid.uuid4()) != ticket_code.gerar(uuid.uuid4())

    def test_mesmo_id_gera_sempre_o_mesmo_codigo(self):
        tid = uuid.uuid4()
        assert ticket_code.gerar(tid) == ticket_code.gerar(tid)

    @pytest.mark.parametrize("lixo", ["", ".", "abc", "a.b.c", "!!!.???", "A" * 60])
    def test_entrada_invalida_nao_quebra(self, lixo):
        assert ticket_code.conferir(lixo) is None

    def test_segredo_diferente_invalida_o_codigo(self, monkeypatch):
        tid = uuid.uuid4()
        codigo = ticket_code.gerar(tid)

        monkeypatch.setenv("TICKET_SECRET", "outro-segredo-completamente-diferente")
        get_settings.cache_clear()
        try:
            assert ticket_code.conferir(codigo) is None
        finally:
            get_settings.cache_clear()
