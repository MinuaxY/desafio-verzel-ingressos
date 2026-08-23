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
class Resultado:
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

    def validar(
        self,
        codigo: str,
        *,
        operador_id: uuid.UUID,
        session_id: uuid.UUID | None = None,
    ) -> Resultado:
        ticket_id = ticket_code.conferir(codigo)
        if ticket_id is None:
            # Código forjado, digitado errado ou QR de outro sistema. Não
            # distinguimos: para quem está na porta, o resultado é o mesmo, e
            # detalhar ajudaria quem estivesse tentando adivinhar.
            return Resultado(INVALID, "Código inválido")

        ingresso = self.db.get(Ticket, ticket_id)
        if ingresso is None:
            return Resultado(INVALID, "Ingresso não encontrado")

        # A sessão é conferida antes do ingresso, e de propósito.
        #
        # Cancelar a sessão já invalida os ingressos dela, então esta checagem
        # é redundante no caminho normal. Ela existe porque a consequência de
        # falhar é grave: alguém entrando numa sala que não vai exibir nada.
        # Se um ingresso escapar da invalidação — por um estado que ainda não
        # previmos, ou por dado antigo —, a porta continua fechada. Mesmo
        # princípio da D6: duas verificações independentes. Ver decisão D30.
        if ingresso.session.status is SessionStatus.CANCELLED:
            return Resultado(
                INVALID,
                f"A sessão de {ingresso.session.movie_title} foi cancelada",
                ingresso,
            )

        if ingresso.status is TicketStatus.CANCELLED:
            return Resultado(INVALID, "Ingresso cancelado", ingresso)

        if ingresso.status is TicketStatus.RESERVED:
            return Resultado(INVALID, "Ingresso não pago", ingresso)

        # A sessão errada é checada antes do reuso de propósito: quem chegou na
        # porta errada precisa ouvir isso, e não "já utilizado" por causa de uma
        # entrada legítima em outra sala.
        if session_id is not None and ingresso.session_id != session_id:
            return Resultado(
                WRONG_SESSION,
                f"Este ingresso é para {ingresso.session.movie_title}, em outra sessão",
                ingresso,
            )

        if ingresso.status is TicketStatus.USED:
            return Resultado(
                ALREADY_USED,
                f"Ingresso já utilizado em {ingresso.used_at:%d/%m às %H:%M}",
                ingresso,
                ingresso.used_at,
            )

        ingresso.status = TicketStatus.USED
        ingresso.used_at = datetime.now(timezone.utc)
        ingresso.used_by_id = operador_id
        self.db.commit()
        self.db.refresh(ingresso)

        return Resultado(
            VALID,
            f"Entrada liberada — {ingresso.sector.name}, poltrona {ingresso.seat_code}",
            ingresso,
            ingresso.used_at,
        )

    def por_share_token(self, token: uuid.UUID) -> Ticket | None:
        """Ingresso aberto por link compartilhado.

        Só leitura: o link mostra o ingresso, mas não é chave de entrada. Ver
        decisão D17.
        """
        from sqlalchemy import select

        return self.db.scalar(select(Ticket).where(Ticket.share_token == token))
