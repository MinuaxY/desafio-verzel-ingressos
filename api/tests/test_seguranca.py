"""Proteções de borda: limite de tentativas, cabeçalhos e vazamento de erro."""
import pytest

from app.core.throttle import MAX_TENTATIVAS, Throttle, tentativas_de_login

CLIENTE = {
    "name": "Cli", "email": "cli@seg.dev", "password": "senhaforte123",
}


@pytest.fixture(autouse=True)
def limpa_throttle():
    tentativas_de_login.limpar_tudo()
    yield
    tentativas_de_login.limpar_tudo()


class TestLimiteDeTentativas:
    """Sem limite, o login aceita quantas senhas por segundo o atacante enviar,
    e nenhuma senha resiste a isso. Ver decisão D26."""

    def test_erra_ate_o_limite_e_e_bloqueado(self, client):
        client.post("/auth/register", json=CLIENTE)

        for _ in range(MAX_TENTATIVAS):
            r = client.post(
                "/auth/login", json={"email": CLIENTE["email"], "password": "erradaerrada"}
            )
            assert r.status_code == 401

        bloqueado = client.post(
            "/auth/login", json={"email": CLIENTE["email"], "password": "erradaerrada"}
        )
        assert bloqueado.status_code == 429
        assert "Retry-After" in bloqueado.headers

    def test_bloqueio_vale_ate_para_a_senha_certa(self, client):
        """Depois de bloqueado, nem acertar libera — senão bastaria acertar na
        tentativa seguinte para zerar a contagem."""
        client.post("/auth/register", json=CLIENTE)
        for _ in range(MAX_TENTATIVAS):
            client.post(
                "/auth/login", json={"email": CLIENTE["email"], "password": "erradaerrada"}
            )

        r = client.post(
            "/auth/login", json={"email": CLIENTE["email"], "password": CLIENTE["password"]}
        )
        assert r.status_code == 429

    def test_acertar_antes_do_limite_zera_a_contagem(self, client):
        """Quem digitou errado e depois acertou não carrega o histórico."""
        client.post("/auth/register", json=CLIENTE)
        for _ in range(MAX_TENTATIVAS - 1):
            client.post(
                "/auth/login", json={"email": CLIENTE["email"], "password": "erradaerrada"}
            )

        certo = client.post(
            "/auth/login", json={"email": CLIENTE["email"], "password": CLIENTE["password"]}
        )
        assert certo.status_code == 200

        # A contagem foi zerada: dá para errar de novo sem cair no bloqueio.
        de_novo = client.post(
            "/auth/login", json={"email": CLIENTE["email"], "password": "erradaerrada"}
        )
        assert de_novo.status_code == 401

    def test_bloqueio_de_uma_conta_nao_atinge_outra(self, client):
        """A chave junta IP e e-mail. Só por IP, uma rede compartilhada
        inteira pararia porque uma pessoa errou a senha."""
        client.post("/auth/register", json=CLIENTE)
        client.post("/auth/register", json={**CLIENTE, "email": "outro@seg.dev"})

        for _ in range(MAX_TENTATIVAS + 1):
            client.post(
                "/auth/login", json={"email": CLIENTE["email"], "password": "erradaerrada"}
            )

        outro = client.post(
            "/auth/login", json={"email": "outro@seg.dev", "password": CLIENTE["password"]}
        )
        assert outro.status_code == 200

    def test_cadastro_nao_e_bloqueado_pelo_login(self, client):
        client.post("/auth/register", json=CLIENTE)
        for _ in range(MAX_TENTATIVAS + 1):
            client.post(
                "/auth/login", json={"email": CLIENTE["email"], "password": "erradaerrada"}
            )

        r = client.post("/auth/register", json={**CLIENTE, "email": "novo@seg.dev"})
        assert r.status_code == 201


class TestThrottleIsolado:
    def test_libera_depois_da_janela(self):
        t = Throttle(maximo=2, janela=0)
        t.registrar("x")
        t.registrar("x")
        assert t.bloqueado("x") == 0

    def test_conta_por_chave(self):
        t = Throttle(maximo=1, janela=60)
        t.registrar("a")
        assert t.bloqueado("a") > 0
        assert t.bloqueado("b") == 0

    def test_liberar_zera(self):
        t = Throttle(maximo=1, janela=60)
        t.registrar("a")
        t.liberar("a")
        assert t.bloqueado("a") == 0

    def test_devolve_segundos_restantes(self):
        t = Throttle(maximo=1, janela=60)
        t.registrar("a")
        assert 1 <= t.bloqueado("a") <= 60


class TestCabecalhos:
    def test_resposta_traz_os_cabecalhos_de_seguranca(self, client):
        h = client.get("/health").headers
        assert h["X-Content-Type-Options"] == "nosniff"
        assert h["X-Frame-Options"] == "DENY"
        assert h["Referrer-Policy"] == "no-referrer"
        assert "camera=()" in h["Permissions-Policy"]

    def test_hsts_so_aparece_sob_https(self, client):
        """Em http, o cabeçalho seria ignorado — ou pior, prenderia o localhost
        de quem estiver avaliando em https."""
        assert "Strict-Transport-Security" not in client.get("/health").headers

        atras_de_proxy = client.get("/health", headers={"x-forwarded-proto": "https"})
        assert "Strict-Transport-Security" in atras_de_proxy.headers

    def test_valem_tambem_para_resposta_de_erro(self, client):
        h = client.get("/sessions/00000000-0000-0000-0000-000000000000").headers
        assert h["X-Content-Type-Options"] == "nosniff"


class TestErroNaoVazaEstrutura:
    def test_validacao_devolve_so_local_e_mensagem(self, client):
        """A resposta padrão do FastAPI inclui `ctx` e `input`, que descrevem o
        parser por dentro e devolvem de volta o que foi enviado."""
        r = client.get("/sessions/nao-e-uuid")
        assert r.status_code == 422

        for erro in r.json()["detail"]:
            assert set(erro.keys()) == {"loc", "msg"}
            assert "ctx" not in erro
            assert "input" not in erro

    def test_corpo_invalido_nao_devolve_o_que_foi_enviado(self, client):
        r = client.post(
            "/auth/register",
            json={"name": "x", "email": "nao-e-email", "password": "curta"},
        )
        assert r.status_code == 422
        assert "nao-e-email" not in r.text
