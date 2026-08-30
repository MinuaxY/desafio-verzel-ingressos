"""Pagamento simulado.

Não há transação financeira nem chamada externa. O desfecho é decidido pelo
número do cartão, do mesmo jeito que os ambientes de teste dos provedores de
verdade funcionam: existe um número que sempre recusa, para que a recusa possa
ser demonstrada sem depender de sorte.

Sorteio aleatório foi descartado justamente por isso — quem estivesse avaliando
não conseguiria provocar a recusa de propósito, e a metade recusada do fluxo
ficaria invisível. Ver decisão D18.
"""
from dataclasses import dataclass

# Números com significado fixo. Os mesmos que a documentação do projeto cita.
CARTAO_RECUSADO = "4000000000000002"
CARTAO_SEM_SALDO = "4000000000009995"

MOTIVOS = {
    CARTAO_RECUSADO: "Cartão recusado pelo emissor",
    CARTAO_SEM_SALDO: "Saldo insuficiente",
}


@dataclass(frozen=True)
class PaymentResult:
    approved: bool
    reason: str | None = None


def _digits_only(numero: str) -> str:
    return "".join(c for c in numero if c.isdigit())


def process(card_number: str, amount_cents: int) -> PaymentResult:
    numero = _digits_only(card_number)

    if not 13 <= len(numero) <= 19:
        return PaymentResult(False, "Número de cartão inválido")

    if numero in MOTIVOS:
        return PaymentResult(False, MOTIVOS[numero])

    if amount_cents <= 0:
        return PaymentResult(False, "Valor inválido")

    return PaymentResult(True)
