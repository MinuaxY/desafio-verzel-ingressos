"""Validação de ingresso na portaria.

Duas conferências, e as duas são necessárias: a assinatura prova que o código
saiu deste sistema, e o banco prova que ele ainda vale. Assinatura sozinha não
impede que o mesmo ingresso entre duas vezes; consulta sozinha não impede que
alguém invente um código.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session as DbSession

from app.core import ticket_code
from app.models.order import Ticket, TicketStatus
from app.models.session import SessionStatus


@dataclass(frozen=True)
class CheckResult:
    result: str
    message: str
    ticket: Ticket | None = None
    used_at: datetime | None = None


VALID = "VALID"
INVALID = "INVALID"
ALREADY_USED = "ALREADY_USED"
WRONG_SESSION = "WRONG_SESSION"


class GateService:
    def __init__(self, db: DbSession) -> None:
        self.db = db

    def check(
        self,
        code: str,
        *,
        operador_id: uuid.UUID,
        session_id: uuid.UUID | None = None,
    ) -> CheckResult:
        ticket_id = ticket_code.verify(code)
        if ticket_id is None:
            # Código forjado, digitado errado ou QR de outro sistema. Não
            # distinguimos: para quem está na porta, o resultado é o mesmo, e
            # detalhar ajudaria quem estivesse tentando adivinhar.
            return CheckResult(INVALID, "Código inválido")

        ticket = self.db.get(Ticket, ticket_id)
        if ticket is None:
            return CheckResult(INVALID, "Ingresso não encontrado")

        # A sessão é conferida antes do ingresso, e de propósito.
        #
        # Cancelar a sessão já invalida os ingressos dela, então esta checagem
        # é redundante no caminho normal. Ela existe porque a consequência de
        # falhar é grave: alguém entrando numa sala que não vai exibir nada.
        # Se um ingresso escapar da invalidação — por um estado que ainda não
        # previmos, ou por dado antigo —, a porta continua fechada. Mesmo
        # princípio da D6: duas verificações independentes. Ver decisão D30.
        if ticket.session.status is SessionStatus.CANCELLED:
            return CheckResult(
                INVALID,
                f"A sessão de {ticket.session.movie_title} foi cancelada",
                ticket,
            )

        if ticket.status is TicketStatus.CANCELLED:
            return CheckResult(INVALID, "Ingresso cancelado", ticket)

        if ticket.status is TicketStatus.RESERVED:
            return CheckResult(INVALID, "Ingresso não pago", ticket)

        # A sessão errada é checada antes do reuso de propósito: quem chegou na
        # porta errada precisa ouvir isso, e não "já utilizado" por causa de uma
        # entrada legítima em outra sala.
        if session_id is not None and ticket.session_id != session_id:
            return CheckResult(
                WRONG_SESSION,
                f"Este ingresso é para {ticket.session.movie_title}, em outra sessão",
                ticket,
            )

        if ticket.status is TicketStatus.USED:
            return CheckResult(
                ALREADY_USED,
                f"Ingresso já utilizado em {ticket.used_at:%d/%m às %H:%M}",
                ticket,
                ticket.used_at,
            )

        ticket.status = TicketStatus.USED
        ticket.used_at = datetime.now(timezone.utc)
        ticket.used_by_id = operador_id
        self.db.commit()
        self.db.refresh(ticket)

        return CheckResult(
            VALID,
            f"Entrada liberada — {ticket.sector.name}, poltrona {ticket.seat_code}",
            ticket,
            ticket.used_at,
        )

    def by_share_token(self, token: uuid.UUID) -> Ticket | None:
        """Ingresso aberto por link compartilhado.

        Só leitura: o link mostra o ingresso, mas não é chave de entrada. Ver
        decisão D17.
        """
        from sqlalchemy import select

        return self.db.scalar(select(Ticket).where(Ticket.share_token == token))
