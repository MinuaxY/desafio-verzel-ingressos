"""Limite de tentativas de login.

A contagem é por **IP e e-mail juntos**: só por IP puniria uma rede compartilhada
inteira quando uma pessoa erra a senha; só por e-mail deixaria alguém bloquear a
conta de outra pessoa de propósito. Ver decisão D26.

Vive em memória, então vale por instância — limitação registrada no README.
"""
import time
from collections import defaultdict, deque

# Folgado para quem digitou errado, inviável para quem está adivinhando.
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 60


class Throttle:
    def __init__(self, maximum: int = MAX_ATTEMPTS, window: int = WINDOW_SECONDS) -> None:
        self.maximum = maximum
        self.window = window
        self._attempts: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, key: str, now: float) -> deque[float]:
        marks = self._attempts[key]
        while marks and now - marks[0] > self.window:
            marks.popleft()
        return marks

    def record(self, key: str) -> None:
        now = time.monotonic()
        self._prune(key, now).append(now)

    def blocked_for(self, key: str) -> int:
        """Segundos que faltam para liberar; 0 quando pode tentar."""
        now = time.monotonic()
        marks = self._prune(key, now)
        if len(marks) < self.maximum:
            return 0
        return max(1, int(self.window - (now - marks[0])))

    def clear(self, key: str) -> None:
        # Chamado no login bem-sucedido: quem acertou não carrega o histórico de
        # erros para a próxima vez.
        self._attempts.pop(key, None)

    def clear_all(self) -> None:
        self._attempts.clear()


login_attempts = Throttle()
