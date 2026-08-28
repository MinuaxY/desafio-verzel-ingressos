"""Edição de sala, exclusão de sessão, criação em lote e filtro por dia."""
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest

from app.catalog.factory import get_catalog_provider
from app.catalog.fixture import FixtureProvider
from app.config import get_settings
from tests.conftest import cria_conta

ORGANIZADOR = {
    "name": "Org", "email": "org@melh.dev", "password": "senhaforte123", "role": "ORGANIZER",
}
OUTRO = {
    "name": "Org2", "email": "org2@melh.dev", "password": "senhaforte123", "role": "ORGANIZER",
}
CARTAO_OK = {"card_number": "4111111111111111", "card_holder": "PAULO V"}

CLIENTE = {
    "name": "Cli", "email": "cli@melh.dev", "password": "senhaforte123", "role": "CUSTOMER",
}

SALA = {
    "name": "Sala Melhorias",
    "location": "Centro",
    "sectors": [{"name": "Plateia", "rows": 2, "seats_per_row": 6, "aisles": [3]}],
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


def cria_sala(client, headers, nome="Sala Melhorias"):
    return client.post("/rooms", json={**SALA, "name": nome}, headers=headers).json()


def cria_sessao(client, headers, sala, *, dias=2, hora=20, publicar=False):
    quando = (datetime.now(timezone.utc) + timedelta(days=dias)).replace(
        hour=hora, minute=0, second=0, microsecond=0
    )
    return client.post(
        "/organizer/sessions",
        json={
            "catalog_id": FixtureProvider().items[0].id,
            "room_id": sala["id"],
            "starts_at": quando.isoformat(),
            "prices": [{"sector_id": s["id"], "price_cents": 3000} for s in sala["sectors"]],
            "publish": publicar,
        },
        headers=headers,
    )


# ==========================================================================
# Edicao de sala
# ==========================================================================


class TestEdicaoDeSala:
    def test_muda_nome_e_endereco(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)

        r = client.patch(
            f"/rooms/{sala['id']}",
            json={"name": "Sala Renomeada", "location": "Zona Sul"},
            headers=headers,
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Sala Renomeada"
        assert r.json()["location"] == "Zona Sul"

    def test_campo_ausente_fica_como_esta(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)

        r = client.patch(f"/rooms/{sala['id']}", json={"name": "Só o nome"}, headers=headers)
        assert r.json()["location"] == "Centro"

    def test_nome_repetido_e_recusado(self, client):
        headers = auth(client, ORGANIZADOR)
        cria_sala(client, headers, "Sala A")
        outra = cria_sala(client, headers, "Sala B")

        r = client.patch(f"/rooms/{outra['id']}", json={"name": "Sala A"}, headers=headers)
        assert r.status_code == 409

    def test_manter_o_proprio_nome_nao_e_conflito(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        r = client.patch(
            f"/rooms/{sala['id']}", json={"name": sala["name"], "location": "Nova"}, headers=headers
        )
        assert r.status_code == 200

    def test_geometria_muda_enquanto_a_sala_e_nova(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)

        r = client.patch(
            f"/rooms/{sala['id']}",
            json={
                "sectors": [
                    {"name": "Plateia", "rows": 4, "seats_per_row": 8, "aisles": [4]},
                    {"name": "VIP", "rows": 1, "seats_per_row": 4, "display_order": 1},
                ]
            },
            headers=headers,
        )
        assert r.status_code == 200
        assert r.json()["capacity"] == 36
        assert [s["name"] for s in r.json()["sectors"]] == ["Plateia", "VIP"]

    def test_geometria_trava_depois_da_primeira_sessao(self, client):
        """Ingresso vendido aponta para uma poltrona específica; mudar o layout
        faria aquele lugar deixar de existir. Ver decisão D29."""
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        cria_sessao(client, headers, sala)

        r = client.patch(
            f"/rooms/{sala['id']}",
            json={"sectors": [{"name": "Plateia", "rows": 9, "seats_per_row": 9}]},
            headers=headers,
        )
        assert r.status_code == 409
        assert "layout" in r.json()["detail"]

    def test_nome_continua_editavel_com_sessao(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        cria_sessao(client, headers, sala)

        r = client.patch(
            f"/rooms/{sala['id']}", json={"name": "Sala 1 (reformada)"}, headers=headers
        )
        assert r.status_code == 200

    def test_geometria_invalida_e_recusada(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)

        r = client.patch(
            f"/rooms/{sala['id']}",
            json={
                "sectors": [
                    {
                        "name": "Plateia",
                        "rows": 2,
                        "seats_per_row": 6,
                        "special_seats": [{"seat_code": "Z9", "kind": "WHEELCHAIR"}],
                    }
                ]
            },
            headers=headers,
        )
        assert r.status_code == 422

    def test_sala_de_outro_responde_404(self, client):
        sala = cria_sala(client, auth(client, ORGANIZADOR))
        r = client.patch(f"/rooms/{sala['id']}", json={"name": "X"}, headers=auth(client, OUTRO))
        assert r.status_code == 404


# ==========================================================================
# Exclusao de sessao
# ==========================================================================


class TestExclusaoDeSessao:
    def test_rascunho_sem_ingresso_e_apagado(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = cria_sessao(client, headers, sala).json()

        apagar = client.delete(f"/organizer/sessions/{sessao['id']}", headers=headers)
        assert apagar.status_code == 204
        assert client.get(
            f"/organizer/sessions/{sessao['id']}", headers=headers
        ).status_code == 404

    def test_sessao_publicada_nao_e_apagada(self, client):
        """Sai do cartaz com despublicar, não com exclusão."""
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = cria_sessao(client, headers, sala, publicar=True).json()

        r = client.delete(f"/organizer/sessions/{sessao['id']}", headers=headers)
        assert r.status_code == 409
        assert "Despublique" in r.json()["detail"]

    def test_sessao_com_ingresso_nao_e_apagada(self, client):
        """Quem comprou precisa continuar enxergando o que comprou."""
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = cria_sessao(client, headers, sala, publicar=True).json()

        cliente = auth(client, CLIENTE)
        client.post(
            "/orders",
            json={
                "session_id": sessao["id"],
                "seats": [{"sector_id": sala["sectors"][0]["id"], "seat_code": "A1"}],
            },
            headers=cliente,
        )
        client.post(f"/organizer/sessions/{sessao['id']}/unpublish", headers=headers)

        r = client.delete(f"/organizer/sessions/{sessao['id']}", headers=headers)
        assert r.status_code == 409
        assert "ingressos" in r.json()["detail"]

    def test_sessao_de_outro_responde_404(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = cria_sessao(client, headers, sala).json()

        r = client.delete(f"/organizer/sessions/{sessao['id']}", headers=auth(client, OUTRO))
        assert r.status_code == 404


class TestEdicaoDeSessaoComIngresso:
    def test_horario_nao_muda_com_ingresso_vendido(self, client):
        """O sistema não tem como avisar quem já comprou."""
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = cria_sessao(client, headers, sala, publicar=True).json()

        client.post(
            "/orders",
            json={
                "session_id": sessao["id"],
                "seats": [{"sector_id": sala["sectors"][0]["id"], "seat_code": "A1"}],
            },
            headers=auth(client, CLIENTE),
        )

        novo = (datetime.now(timezone.utc) + timedelta(days=5)).replace(microsecond=0)
        r = client.patch(
            f"/organizer/sessions/{sessao['id']}",
            json={"starts_at": novo.isoformat()},
            headers=headers,
        )
        assert r.status_code == 409

    def test_preco_continua_editavel_com_ingresso(self, client):
        """Preço novo vale para quem ainda vai comprar; não mexe no que já foi
        vendido, porque o ingresso guarda o valor pago."""
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = cria_sessao(client, headers, sala, publicar=True).json()

        client.post(
            "/orders",
            json={
                "session_id": sessao["id"],
                "seats": [{"sector_id": sala["sectors"][0]["id"], "seat_code": "A1"}],
            },
            headers=auth(client, CLIENTE),
        )

        r = client.patch(
            f"/organizer/sessions/{sessao['id']}",
            json={"prices": [{"sector_id": sala["sectors"][0]["id"], "price_cents": 4500}]},
            headers=headers,
        )
        assert r.status_code == 200
        assert r.json()["min_price_cents"] == 4500


# ==========================================================================
# Criacao em lote
# ==========================================================================


def dias_a_frente(*offsets: int) -> list[str]:
    hoje = datetime.now(timezone.utc).date()
    return [(hoje + timedelta(days=o)).isoformat() for o in offsets]


class TestCriacaoEmLote:
    def corpo(self, sala, datas, hora="19:00:00", **extra):
        return {
            "catalog_id": FixtureProvider().items[0].id,
            "room_id": sala["id"],
            "dates": datas,
            "time_of_day": hora,
            "prices": [{"sector_id": s["id"], "price_cents": 3000} for s in sala["sectors"]],
            **extra,
        }

    def test_cria_uma_sessao_por_dia(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)

        r = client.post(
            "/organizer/sessions/batch",
            json=self.corpo(sala, dias_a_frente(2, 3, 4)),
            headers=headers,
        )
        assert r.status_code == 201
        assert len(r.json()["created"]) == 3
        assert r.json()["skipped"] == []

    def test_todas_com_o_mesmo_horario_e_filme(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)

        criadas = client.post(
            "/organizer/sessions/batch",
            json=self.corpo(sala, dias_a_frente(2, 5), hora="21:30:00"),
            headers=headers,
        ).json()["created"]

        titulos = {s["movie"]["title"] for s in criadas}
        assert len(titulos) == 1
        for s in criadas:
            assert s["starts_at"].endswith(("00:30:00Z", "21:30:00Z"))

    def test_dias_ocupados_sao_pulados_e_reportados(self, client):
        """Um dia ocupado não joga fora o trabalho de escolher os outros."""
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)

        # Ocupa o dia 3 no mesmo horário.
        client.post(
            "/organizer/sessions/batch",
            json=self.corpo(sala, dias_a_frente(3)),
            headers=headers,
        )

        r = client.post(
            "/organizer/sessions/batch",
            json=self.corpo(sala, dias_a_frente(2, 3, 4)),
            headers=headers,
        )
        corpo = r.json()
        assert len(corpo["created"]) == 2
        assert len(corpo["skipped"]) == 1
        assert corpo["skipped"][0]["date"] == dias_a_frente(3)[0]
        assert "sess" in corpo["skipped"][0]["reason"].lower()

    def test_data_no_passado_e_pulada(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)

        r = client.post(
            "/organizer/sessions/batch",
            json=self.corpo(sala, dias_a_frente(-3, 2)),
            headers=headers,
        )
        corpo = r.json()
        assert len(corpo["created"]) == 1
        assert len(corpo["skipped"]) == 1
        assert "passaram" in corpo["skipped"][0]["reason"]

    def test_datas_repetidas_viram_uma_so(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        um_dia = dias_a_frente(2)

        r = client.post(
            "/organizer/sessions/batch",
            json=self.corpo(sala, um_dia * 3),
            headers=headers,
        )
        assert len(r.json()["created"]) == 1

    def test_pode_publicar_o_lote_inteiro(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)

        criadas = client.post(
            "/organizer/sessions/batch",
            json=self.corpo(sala, dias_a_frente(2, 3), publish=True),
            headers=headers,
        ).json()["created"]

        assert all(s["status"] == "PUBLISHED" for s in criadas)
        assert client.get("/sessions").json()["total"] == 2

    def test_sem_data_e_recusado(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        r = client.post(
            "/organizer/sessions/batch", json=self.corpo(sala, []), headers=headers
        )
        assert r.status_code == 422

    def test_cliente_nao_cria_lote(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        r = client.post(
            "/organizer/sessions/batch",
            json=self.corpo(sala, dias_a_frente(2)),
            headers=auth(client, CLIENTE),
        )
        assert r.status_code == 403


# ==========================================================================
# Filtro por dia na vitrine
# ==========================================================================


class TestFiltroPorDia:
    def test_lista_so_as_sessoes_do_dia(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        cria_sessao(client, headers, sala, dias=2, hora=19, publicar=True)
        cria_sessao(client, headers, sala, dias=5, hora=19, publicar=True)

        assert client.get("/sessions").json()["total"] == 2

        alvo = client.get("/sessions").json()["items"][0]["starts_at"][:10]
        so_um_dia = client.get("/sessions", params={"dia": alvo}).json()
        assert so_um_dia["total"] == 1

    def test_dia_sem_sessao_devolve_vazio(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        cria_sessao(client, headers, sala, dias=2, publicar=True)

        vazio = (date.today() + timedelta(days=9)).isoformat()
        assert client.get("/sessions", params={"dia": vazio}).json()["total"] == 0

    def test_filtro_por_dia_combina_com_busca(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        cria_sessao(client, headers, sala, dias=2, publicar=True)

        alvo = client.get("/sessions").json()["items"][0]
        dia = alvo["starts_at"][:10]

        achou = client.get("/sessions", params={"dia": dia, "busca": alvo["title"][:5]})
        assert achou.json()["total"] == 1
        assert client.get("/sessions", params={"dia": dia, "busca": "zzzz"}).json()["total"] == 0

    def test_dia_invalido_e_recusado(self, client):
        assert client.get("/sessions", params={"dia": "ontem"}).status_code == 422


class TestDiasEmCartaz:
    def test_lista_os_dias_com_sessao_e_a_contagem(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        cria_sessao(client, headers, sala, dias=2, hora=16, publicar=True)
        cria_sessao(client, headers, sala, dias=2, hora=21, publicar=True)
        cria_sessao(client, headers, sala, dias=6, hora=19, publicar=True)

        dias = client.get("/sessions/days").json()
        assert len(dias) == 2
        assert sorted(d["total"] for d in dias) == [1, 2]

    def test_rascunho_nao_conta(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        cria_sessao(client, headers, sala, dias=2, publicar=False)

        assert client.get("/sessions/days").json() == []

    def test_e_publico(self, client):
        assert client.get("/sessions/days").status_code == 200

    def test_a_rota_nao_e_confundida_com_um_id(self, client):
        """'days' viria antes de '{session_id}' no roteador; se a ordem estiver
        errada, esta chamada devolve 422 tentando ler 'days' como UUID."""
        r = client.get("/sessions/days")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ==========================================================================
# Cancelamento de sessao (D30)
# ==========================================================================


def compra_paga(client, sessao, sala, cliente=CLIENTE, assento="A1"):
    """Compra uma poltrona e paga, devolvendo o pedido já com o ingresso."""
    h = auth(client, cliente)
    pedido = client.post(
        "/orders",
        json={
            "session_id": sessao["id"],
            "seats": [{"sector_id": sala["sectors"][0]["id"], "seat_code": assento}],
        },
        headers=h,
    ).json()
    pago = client.post(f"/orders/{pedido['id']}/pay", json=CARTAO_OK, headers=h).json()
    return pago, h


class TestCancelamentoDeSessao:
    def test_sessao_vazia_cancela(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = cria_sessao(client, headers, sala, publicar=True).json()

        r = client.post(f"/organizer/sessions/{sessao['id']}/cancel", headers=headers)
        assert r.status_code == 200
        assert r.json()["status"] == "CANCELLED"

    def test_com_ingresso_vendido_recusa(self, client):
        """O ponto da D30: cancelar não avisa nem reembolsa ninguém, então
        cancelar por cima de quem comprou seria só esconder o problema."""
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = cria_sessao(client, headers, sala, publicar=True).json()
        compra_paga(client, sessao, sala)

        r = client.post(f"/organizer/sessions/{sessao['id']}/cancel", headers=headers)
        assert r.status_code == 409
        assert "1 ingresso" in r.json()["detail"]

        # e a sessao continua de pe
        atual = client.get(f"/organizer/sessions/{sessao['id']}", headers=headers).json()
        assert atual["status"] == "PUBLISHED"

    def test_reserva_nao_paga_tambem_segura(self, client):
        """A poltrona está fora do estoque desde a reserva; para o mapa de
        assentos ela é tão ocupada quanto uma paga."""
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = cria_sessao(client, headers, sala, publicar=True).json()

        client.post(
            "/orders",
            json={
                "session_id": sessao["id"],
                "seats": [{"sector_id": sala["sectors"][0]["id"], "seat_code": "A1"}],
            },
            headers=auth(client, CLIENTE),
        )

        r = client.post(f"/organizer/sessions/{sessao['id']}/cancel", headers=headers)
        assert r.status_code == 409

    def test_desistencia_do_cliente_libera_o_cancelamento(self, client):
        """Se todo mundo desistiu, a sessão está vazia de novo e volta a poder
        ser cancelada."""
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = cria_sessao(client, headers, sala, publicar=True).json()
        pedido, h_cliente = compra_paga(client, sessao, sala)

        assert client.post(
            f"/organizer/sessions/{sessao['id']}/cancel", headers=headers
        ).status_code == 409

        client.post(f"/orders/{pedido['id']}/cancel", headers=h_cliente)

        assert client.post(
            f"/organizer/sessions/{sessao['id']}/cancel", headers=headers
        ).status_code == 200

    def test_despublicar_continua_livre_com_ingresso(self, client):
        """Despublicar é o caminho para tirar do cartaz sem quebrar promessa:
        para de vender e quem já comprou continua com o ingresso de pé."""
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = cria_sessao(client, headers, sala, publicar=True).json()
        pedido, _ = compra_paga(client, sessao, sala)

        r = client.post(f"/organizer/sessions/{sessao['id']}/unpublish", headers=headers)
        assert r.status_code == 200
        assert r.json()["status"] == "DRAFT"

        # o ingresso nao foi tocado
        porteiro = auth(client, {
            "name": "Porteiro", "email": "p@melh.dev", "password": "senhaforte123", "role": "GATE",
        })
        codigo = pedido["tickets"][0]["code"]
        assert client.post(
            "/gate/validate", json={"code": codigo}, headers=porteiro
        ).json()["result"] == "VALID"

    def test_o_painel_informa_quantos_foram_vendidos(self, client):
        """É o número que desabilita o botão de cancelar na interface."""
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = cria_sessao(client, headers, sala, publicar=True).json()

        lista = client.get("/organizer/sessions", headers=headers).json()
        assert lista[0]["tickets_sold"] == 0

        compra_paga(client, sessao, sala)
        lista = client.get("/organizer/sessions", headers=headers).json()
        assert lista[0]["tickets_sold"] == 1


class TestPortariaEsessaoCancelada:
    def test_ingresso_de_sessao_cancelada_nao_entra(self, client):
        """Segunda verificação, independente do estado do ingresso.

        Hoje o caminho normal não chega aqui, porque cancelar exige sessão
        vazia. A checagem existe para o caso de um ingresso escapar: a
        consequência de errar é alguém entrar numa sala que não vai exibir
        nada. Mesmo princípio da D6.
        """
        from app.models.session import Session, SessionStatus

        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = cria_sessao(client, headers, sala, publicar=True).json()
        pedido, _ = compra_paga(client, sessao, sala)

        # Cancelamento forcado no banco: a API recusaria, e o que se testa aqui
        # e justamente a rede de seguranca embaixo dela.
        from tests.conftest import TestSession

        db = TestSession()
        s = db.get(Session, uuid.UUID(sessao["id"]))
        s.status = SessionStatus.CANCELLED
        db.commit()
        db.close()

        porteiro = auth(client, {
            "name": "Porteiro Dois", "email": "p2@melh.dev",
            "password": "senhaforte123", "role": "GATE",
        })
        r = client.post(
            "/gate/validate", json={"code": pedido["tickets"][0]["code"]}, headers=porteiro
        ).json()
        assert r["result"] == "INVALID"
        assert "cancelada" in r["message"].lower()


class TestCancelamentoEmMassaDePedidos:
    def test_esvazia_a_sessao_e_libera_o_cancelamento(self, client):
        """O caminho completo: a sessão que não pode ser cancelada passa a
        poder, depois que o organizador desfez as compras explicitamente."""
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = cria_sessao(client, headers, sala, publicar=True).json()
        compra_paga(client, sessao, sala, assento="A1")

        assert client.post(
            f"/organizer/sessions/{sessao['id']}/cancel", headers=headers
        ).status_code == 409

        r = client.post(f"/organizer/sessions/{sessao['id']}/cancel-orders", headers=headers)
        assert r.status_code == 200
        assert r.json()["cancelled"] == 1
        assert r.json()["session"]["tickets_sold"] == 0

        assert client.post(
            f"/organizer/sessions/{sessao['id']}/cancel", headers=headers
        ).status_code == 200

    def test_despublica_antes_de_esvaziar(self, client):
        """Não dá para esvaziar uma sessão que continua vendendo."""
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = cria_sessao(client, headers, sala, publicar=True).json()
        compra_paga(client, sessao, sala)

        r = client.post(f"/organizer/sessions/{sessao['id']}/cancel-orders", headers=headers)
        assert r.json()["session"]["status"] == "DRAFT"

        # e a sessao fora do cartaz nao aceita compra nova
        nova = client.post(
            "/orders",
            json={
                "session_id": sessao["id"],
                "seats": [{"sector_id": sala["sectors"][0]["id"], "seat_code": "A2"}],
            },
            headers=auth(client, {
                "name": "Outra Cliente", "email": "outra@melh.dev",
                "password": "senhaforte123", "role": "CUSTOMER",
            }),
        )
        # 404 e nao 409: sessao fora do cartaz nao existe para quem compra.
        assert nova.status_code == 404

    def test_o_cliente_ve_que_foi_o_cinema_que_cancelou(self, client):
        """O ponto todo da operação: sem essa marca, o cliente leria apenas
        'cancelado' e concluiria que a desistência foi dele."""
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = cria_sessao(client, headers, sala, publicar=True).json()
        pedido, h_cliente = compra_paga(client, sessao, sala)

        client.post(f"/organizer/sessions/{sessao['id']}/cancel-orders", headers=headers)

        atual = client.get(f"/orders/{pedido['id']}", headers=h_cliente).json()
        assert atual["status"] == "CANCELLED"
        assert atual["cancelled_by_organizer"] is True

    def test_desistencia_do_cliente_nao_e_marcada_como_do_cinema(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = cria_sessao(client, headers, sala, publicar=True).json()
        pedido, h_cliente = compra_paga(client, sessao, sala)

        client.post(f"/orders/{pedido['id']}/cancel", headers=h_cliente)

        atual = client.get(f"/orders/{pedido['id']}", headers=h_cliente).json()
        assert atual["cancelled_by_organizer"] is False

    def test_o_ingresso_sai_da_carteira(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = cria_sessao(client, headers, sala, publicar=True).json()
        _, h_cliente = compra_paga(client, sessao, sala)

        assert len(client.get("/me/tickets", headers=h_cliente).json()) == 1
        client.post(f"/organizer/sessions/{sessao['id']}/cancel-orders", headers=headers)
        assert client.get("/me/tickets", headers=h_cliente).json() == []

    def test_o_qr_para_de_passar_na_portaria(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = cria_sessao(client, headers, sala, publicar=True).json()
        pedido, _ = compra_paga(client, sessao, sala)
        codigo = pedido["tickets"][0]["code"]

        client.post(f"/organizer/sessions/{sessao['id']}/cancel-orders", headers=headers)

        porteiro = auth(client, {
            "name": "Porteiro Tres", "email": "p3@melh.dev",
            "password": "senhaforte123", "role": "GATE",
        })
        r = client.post("/gate/validate", json={"code": codigo}, headers=porteiro).json()
        assert r["result"] == "INVALID"

    def test_quem_ja_entrou_continua_tendo_entrado(self, client):
        """Ingresso utilizado é registro de quem passou pela porta. Cancelar o
        pedido depois não pode reescrever esse fato."""
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = cria_sessao(client, headers, sala, publicar=True).json()
        pedido, _ = compra_paga(client, sessao, sala)

        porteiro = auth(client, {
            "name": "Porteiro Quatro", "email": "p4@melh.dev",
            "password": "senhaforte123", "role": "GATE",
        })
        client.post(
            "/gate/validate", json={"code": pedido["tickets"][0]["code"]}, headers=porteiro
        )

        client.post(f"/organizer/sessions/{sessao['id']}/cancel-orders", headers=headers)

        r = client.post(
            "/gate/validate", json={"code": pedido["tickets"][0]["code"]}, headers=porteiro
        ).json()
        assert r["result"] == "ALREADY_USED"

        # e a poltrona dele continua ocupada, entao a sessao nao ficou "vazia"
        assert client.post(
            f"/organizer/sessions/{sessao['id']}/cancel", headers=headers
        ).status_code == 409

    def test_sessao_sem_pedido_nenhum_devolve_zero(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = cria_sessao(client, headers, sala, publicar=True).json()

        r = client.post(f"/organizer/sessions/{sessao['id']}/cancel-orders", headers=headers)
        assert r.status_code == 200
        assert r.json()["cancelled"] == 0

    def test_sessao_de_outro_organizador_nao_e_alcancavel(self, client):
        dono = auth(client, ORGANIZADOR)
        sala = cria_sala(client, dono)
        sessao = cria_sessao(client, dono, sala, publicar=True).json()
        compra_paga(client, sessao, sala)

        r = client.post(
            f"/organizer/sessions/{sessao['id']}/cancel-orders", headers=auth(client, OUTRO)
        )
        assert r.status_code == 404

    def test_cliente_nao_cancela_pedido_dos_outros(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = cria_sessao(client, headers, sala, publicar=True).json()

        r = client.post(
            f"/organizer/sessions/{sessao['id']}/cancel-orders", headers=auth(client, CLIENTE)
        )
        assert r.status_code == 403


class TestSessaoCanceladaLiberaOHorario:
    def test_da_para_recriar_a_sessao_cancelada(self, client):
        """O impasse: cancelar nao tem volta, e a cancelada segurava o horario
        para sempre. Sessao cancelada nao vai acontecer, entao a sala esta
        livre. Ver decisao D31."""
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = cria_sessao(client, headers, sala, publicar=True).json()
        client.post(f"/organizer/sessions/{sessao['id']}/cancel", headers=headers)

        r = cria_sessao(client, headers, sala, publicar=True)
        assert r.status_code == 201
        assert r.json()["id"] != sessao["id"]

    def test_duas_sessoes_vivas_continuam_brigando_pela_sala(self, client):
        """A trava original nao foi afrouxada: so parou de contar a cancelada."""
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        cria_sessao(client, headers, sala, publicar=True)

        assert cria_sessao(client, headers, sala, publicar=True).status_code == 409

    def test_rascunho_tambem_continua_ocupando(self, client):
        """Rascunho vai acontecer assim que for publicado."""
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        cria_sessao(client, headers, sala, publicar=False)

        assert cria_sessao(client, headers, sala, publicar=True).status_code == 409

    def test_o_lote_nao_pula_mais_o_dia_da_cancelada(self, client):
        """O lote usava a mesma checagem e pulava o dia com um motivo falso."""
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = cria_sessao(client, headers, sala, dias=3, hora=20, publicar=True).json()
        client.post(f"/organizer/sessions/{sessao['id']}/cancel", headers=headers)

        r = client.post(
            "/organizer/sessions/batch",
            json={
                "catalog_id": FixtureProvider().items[0].id,
                "room_id": sala["id"],
                "dates": dias_a_frente(3, 4),
                "time_of_day": "20:00",
                "prices": [
                    {"sector_id": s["id"], "price_cents": 3000} for s in sala["sectors"]
                ],
                "publish": True,
            },
            headers=headers,
        ).json()
        assert len(r["created"]) == 2
        assert r["skipped"] == []

    def test_mover_uma_sessao_para_o_horario_da_cancelada(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        cancelada = cria_sessao(client, headers, sala, dias=3, hora=20).json()
        client.post(f"/organizer/sessions/{cancelada['id']}/cancel", headers=headers)

        outra = cria_sessao(client, headers, sala, dias=5, hora=22).json()
        quando = (datetime.now(timezone.utc) + timedelta(days=3)).replace(
            hour=20, minute=0, second=0, microsecond=0
        )
        r = client.patch(
            f"/organizer/sessions/{outra['id']}",
            json={"starts_at": quando.isoformat()},
            headers=headers,
        )
        assert r.status_code == 200


class TestExclusaoDeSessaoCancelada:
    def test_cancelada_que_nunca_vendeu_pode_ser_apagada(self, client):
        """Ela não é histórico de coisa nenhuma: estava vazia quando foi
        cancelada, senão o cancelamento teria sido recusado."""
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = cria_sessao(client, headers, sala, publicar=True).json()
        client.post(f"/organizer/sessions/{sessao['id']}/cancel", headers=headers)

        assert client.delete(
            f"/organizer/sessions/{sessao['id']}", headers=headers
        ).status_code == 204
        assert client.get("/organizer/sessions", headers=headers).json() == []

    def test_cancelada_que_teve_pedido_fica_como_registro(self, client):
        """Alguém pode precisar rastrear o que aconteceu com aquela compra."""
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = cria_sessao(client, headers, sala, publicar=True).json()
        compra_paga(client, sessao, sala)
        client.post(f"/organizer/sessions/{sessao['id']}/cancel-orders", headers=headers)
        client.post(f"/organizer/sessions/{sessao['id']}/cancel", headers=headers)

        assert client.delete(
            f"/organizer/sessions/{sessao['id']}", headers=headers
        ).status_code == 409

    def test_o_painel_diz_qual_das_duas_e(self, client):
        """É o campo que decide se o botão de excluir aparece."""
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        limpa = cria_sessao(client, headers, sala, dias=2, publicar=True).json()
        suja = cria_sessao(client, headers, sala, dias=4, publicar=True).json()
        compra_paga(client, suja, sala)
        client.post(f"/organizer/sessions/{suja['id']}/cancel-orders", headers=headers)

        painel = {s["id"]: s for s in client.get("/organizer/sessions", headers=headers).json()}
        assert painel[limpa["id"]]["has_tickets"] is False
        assert painel[suja["id"]]["has_tickets"] is True
        # os pedidos foram cancelados, entao nenhuma das duas ocupa poltrona
        assert painel[suja["id"]]["tickets_sold"] == 0


class TestDefeitosDaRevisao:
    """Três defeitos encontrados na revisão de 22/08. Ver decisão D33."""

    def test_sessao_de_graca_e_recusada(self, client):
        """Preço zero deixava o cliente com um pedido que nunca podia ser pago:
        o pagamento simulado recusa valor zero, e a poltrona ficava presa até
        a reserva expirar. A tela de criação já exigia preço; a API é que
        discordava dela."""
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        quando = (datetime.now(timezone.utc) + timedelta(days=2)).replace(
            hour=20, minute=0, second=0, microsecond=0
        )
        r = client.post(
            "/organizer/sessions",
            json={
                "catalog_id": FixtureProvider().items[0].id,
                "room_id": sala["id"],
                "starts_at": quando.isoformat(),
                "prices": [{"sector_id": sala["sectors"][0]["id"], "price_cents": 0}],
            },
            headers=headers,
        )
        assert r.status_code == 422

    def test_um_centavo_continua_valendo(self, client):
        """A trava é contra o zero, não contra preço baixo."""
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        quando = (datetime.now(timezone.utc) + timedelta(days=2)).replace(
            hour=20, minute=0, second=0, microsecond=0
        )
        r = client.post(
            "/organizer/sessions",
            json={
                "catalog_id": FixtureProvider().items[0].id,
                "room_id": sala["id"],
                "starts_at": quando.isoformat(),
                "prices": [{"sector_id": sala["sectors"][0]["id"], "price_cents": 1}],
            },
            headers=headers,
        )
        assert r.status_code == 201

    def test_edicao_tambem_nao_zera_o_preco(self, client):
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = cria_sessao(client, headers, sala).json()

        r = client.patch(
            f"/organizer/sessions/{sessao['id']}",
            json={"prices": [{"sector_id": sala["sectors"][0]["id"], "price_cents": 0}]},
            headers=headers,
        )
        assert r.status_code == 422

    def test_a_rota_andaime_nao_existe_mais(self, client):
        """Ela prometia sair quando os endpoints reais valessem, e ficou."""
        headers = auth(client, ORGANIZADOR)
        assert client.get("/auth/organizer-only", headers=headers).status_code == 404

    def test_a_portaria_ve_a_sessao_que_ja_comecou(self, client):
        """O defeito: a sessão sumia da lista no instante em que começava, com
        o público ainda entrando, e o operador perdia a checagem de sessão
        errada bem na hora em que ela serve."""
        import uuid as U

        from app.models.session import Session

        from tests.conftest import TestSession

        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = cria_sessao(client, headers, sala, publicar=True).json()

        db = TestSession()
        obj = db.get(Session, U.UUID(sessao["id"]))
        obj.starts_at = datetime.now(timezone.utc) - timedelta(minutes=20)
        db.commit()
        db.close()

        porteiro = auth(client, {
            "name": "Porteiro Cinco", "email": "p5@melh.dev",
            "password": "senhaforte123", "role": "GATE",
        })
        # a vitrine, corretamente, ja nao mostra
        assert client.get("/sessions").json()["total"] == 0
        # a portaria, sim
        lista = client.get("/gate/sessions", headers=porteiro).json()
        assert [s["id"] for s in lista] == [sessao["id"]]

    def test_a_portaria_nao_ve_a_sessao_de_ontem(self, client):
        """A janela é do turno, não do histórico."""
        import uuid as U

        from app.models.session import Session

        from tests.conftest import TestSession

        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers)
        sessao = cria_sessao(client, headers, sala, publicar=True).json()

        db = TestSession()
        obj = db.get(Session, U.UUID(sessao["id"]))
        obj.starts_at = datetime.now(timezone.utc) - timedelta(days=1)
        db.commit()
        db.close()

        porteiro = auth(client, {
            "name": "Porteiro Seis", "email": "p6@melh.dev",
            "password": "senhaforte123", "role": "GATE",
        })
        assert client.get("/gate/sessions", headers=porteiro).json() == []

    def test_so_a_portaria_ve_essa_lista(self, client):
        headers = auth(client, ORGANIZADOR)
        assert client.get("/gate/sessions", headers=headers).status_code == 403
        assert client.get("/gate/sessions", headers=auth(client, CLIENTE)).status_code == 403
        assert client.get("/gate/sessions").status_code == 401


class TestPrecoPertenceASalaDaSessao:
    """A invariante mora no banco, não só no serviço. Ver decisão D35.

    Antes, `session_id` e `sector_id` referenciavam suas tabelas de forma
    independente: nada impedia gravar o preço de um setor de outra sala. O
    serviço conferia, e invariante que vive apenas no serviço é invariante que
    a próxima rota esquece.
    """

    def test_o_banco_recusa_setor_de_outra_sala(self, client):
        """Escrito direto no banco, por baixo do serviço — que é justamente o
        caminho que a checagem em Python não cobre."""
        import uuid as U

        from sqlalchemy.exc import IntegrityError

        from app.models.session import SessionSectorPrice

        from tests.conftest import TestSession

        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers, nome="Sala A")
        outra = cria_sala(client, headers, nome="Sala B")
        sessao = cria_sessao(client, headers, sala).json()

        db = TestSession()
        try:
            db.add(
                SessionSectorPrice(
                    session_id=U.UUID(sessao["id"]),
                    sector_id=U.UUID(outra["sectors"][0]["id"]),
                    room_id=U.UUID(sala["id"]),
                    price_cents=3000,
                )
            )
            with pytest.raises(IntegrityError):
                db.commit()
        finally:
            db.rollback()
            db.close()

        # a sessão continua com os preços que tinha
        atual = client.get(f"/organizer/sessions/{sessao['id']}", headers=headers).json()
        assert len(atual["prices"]) == len(sala["sectors"])

    def test_o_banco_recusa_sala_que_nao_e_a_da_sessao(self, client):
        """A outra metade da prova: o setor até é da sala informada, mas a
        sessão não é."""
        import uuid as U

        from sqlalchemy.exc import IntegrityError

        from app.models.session import SessionSectorPrice

        from tests.conftest import TestSession

        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers, nome="Sala C")
        outra = cria_sala(client, headers, nome="Sala D")
        sessao = cria_sessao(client, headers, sala).json()

        db = TestSession()
        try:
            db.add(
                SessionSectorPrice(
                    session_id=U.UUID(sessao["id"]),
                    sector_id=U.UUID(outra["sectors"][0]["id"]),
                    room_id=U.UUID(outra["id"]),
                    price_cents=3000,
                )
            )
            with pytest.raises(IntegrityError):
                db.commit()
        finally:
            db.rollback()
            db.close()

    def test_o_banco_recusa_preco_zerado(self, client):
        """O `CheckConstraint` acompanha o mínimo da API. Ver decisão D33."""
        import uuid as U

        from sqlalchemy.exc import IntegrityError

        from app.models.session import SessionSectorPrice

        from tests.conftest import TestSession

        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers, nome="Sala E")
        sessao = cria_sessao(client, headers, sala).json()

        db = TestSession()
        try:
            db.add(
                SessionSectorPrice(
                    session_id=U.UUID(sessao["id"]),
                    sector_id=U.UUID(sala["sectors"][0]["id"]),
                    room_id=U.UUID(sala["id"]),
                    price_cents=0,
                )
            )
            with pytest.raises(IntegrityError):
                db.commit()
        finally:
            db.rollback()
            db.close()

    def test_a_api_continua_recusando_com_mensagem_legivel(self, client):
        """A trava do banco é rede de segurança, não substituta: quem passa
        pela API precisa de erro explicado, não de violação de constraint."""
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers, nome="Sala F")
        outra = cria_sala(client, headers, nome="Sala G")
        quando = (datetime.now(timezone.utc) + timedelta(days=2)).replace(
            hour=20, minute=0, second=0, microsecond=0
        )

        r = client.post(
            "/organizer/sessions",
            json={
                "catalog_id": FixtureProvider().items[0].id,
                "room_id": sala["id"],
                "starts_at": quando.isoformat(),
                "prices": [{"sector_id": outra["sectors"][0]["id"], "price_cents": 3000}],
            },
            headers=headers,
        )
        assert r.status_code == 422
        assert "preço" in r.json()["detail"].lower()

    def test_apagar_a_sala_leva_os_precos_junto(self, client):
        """A chave composta manteve o CASCADE que as chaves simples tinham."""
        headers = auth(client, ORGANIZADOR)
        sala = cria_sala(client, headers, nome="Sala H")
        cria_sessao(client, headers, sala)

        assert client.delete(f"/rooms/{sala['id']}", headers=headers).status_code == 409
