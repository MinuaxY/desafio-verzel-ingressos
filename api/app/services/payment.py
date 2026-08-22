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
class ResultadoPagamento:
    aprovado: bool
    motivo: str | None = None


def _so_digitos(numero: str) -> str:
    return "".join(c for c in numero if c.isdigit())


def processar(card_number: str, valor_cents: int) -> ResultadoPagamento:
    numero = _so_digitos(card_number)

    if not 13 <= len(numero) <= 19:
        return ResultadoPagamento(False, "Número de cartão inválido")

    if numero in MOTIVOS:
        return ResultadoPagamento(False, MOTIVOS[numero])

    if valor_cents <= 0:
        return ResultadoPagamento(False, "Valor inválido")

    return ResultadoPagamento(True)
