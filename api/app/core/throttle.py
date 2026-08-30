"""Limite de tentativas.

Sem isto, o login aceita quantas senhas por segundo o atacante conseguir
enviar — e nenhuma senha resiste a isso. O bloqueio não precisa ser
sofisticado para acabar com o ataque: basta tornar cada tentativa cara.

A contagem é por **IP e e-mail juntos**. Só por IP puniria uma rede
compartilhada inteira quando uma pessoa erra a senha; só por e-mail deixaria
um atacante enumerar contas a partir de um IP só, e ainda permitiria bloquear
a conta de outra pessoa de propósito.

Vive em memória, então vale por instância. Com mais de um processo, cada um
teria a própria contagem — a mesma limitação do cache do catálogo, e a mesma
resposta: Redis seria o passo seguinte se houvesse mais de uma instância. Para
um atacante, mesmo assim, o custo sobe na proporção do número de instâncias.
"""
import time
from collections import defaultdict, deque

# Cinco tentativas por minuto: folgado para quem digitou errado, inviável para
# quem está adivinhando.
MAX_TENTATIVAS = 5
JANELA_SEGUNDOS = 60


class Throttle:
    def __init__(self, maximo: int = MAX_TENTATIVAS, janela: int = JANELA_SEGUNDOS) -> None:
        self.maximo = maximo
        self.janela = janela
        self._tentativas: dict[str, deque[float]] = defaultdict(deque)

    def _limpa(self, key: str, now: float) -> deque[float]:
        marcas = self._tentativas[key]
        while marcas and now - marcas[0] > self.janela:
            marcas.popleft()
        return marcas

    def registrar(self, key: str) -> None:
        """Conta uma tentativa malsucedida."""
        now = time.monotonic()
        self._limpa(key, now).append(now)

    def blocked_for(self, key: str) -> int:
        """Segundos que faltam para liberar; 0 quando pode tentar."""
        now = time.monotonic()
        marcas = self._limpa(key, now)
        if len(marcas) < self.maximo:
            return 0
        return max(1, int(self.janela - (now - marcas[0])))

    def liberar(self, key: str) -> None:
        """Chamado no login bem-sucedido: quem acertou não carrega o histórico
        de erros para a próxima vez."""
        self._tentativas.pop(key, None)

    def limpar_tudo(self) -> None:
        self._tentativas.clear()


login_attempts = Throttle()
