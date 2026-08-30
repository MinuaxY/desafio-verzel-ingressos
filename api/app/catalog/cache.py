"""Cache em memória com expiração por tempo.

Protege o rate limit da API externa e deixa o desenvolvimento mais rápido.
Suficiente para uma instância; um segundo processo teria o próprio cache.
Trocar por Redis seria o passo seguinte se houvesse mais de uma instância.
"""
import time
from typing import Any


class TTLCache:
    def __init__(self, ttl_seconds: int) -> None:
        self.ttl = ttl_seconds
        self._data: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        expira_em, amount = entry
        if time.monotonic() > expira_em:
            del self._data[key]
            return None
        return amount

    def set(self, key: str, value: Any) -> None:
        self._data[key] = (time.monotonic() + self.ttl, value)

    def clear(self) -> None:
        self._data.clear()
