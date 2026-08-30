"""Compra de ingressos: reserva, pagamento e emissão."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from app.core import ticket_code
from app.models.order import OCCUPY_SEAT, Order, OrderStatus, Ticket, TicketStatus
from app.models.session import Session, SessionStatus
from app.schemas.order import OrderCreate, SeatSelection
from app.services import payment


class SessionNotAvailable(Exception):
    """A sessão não existe, não está publicada ou já começou."""


class SeatDoesNotExist(Exception):
    def __init__(self, codigos: list[str]) -> None:
        self.codigos = codigos
        super().__init__(", ".join(codigos))


class SeatTaken(Exception):
    def __init__(self, codigos: list[str]) -> None:
        self.codigos = codigos
        super().__init__(", ".join(codigos))


class DuplicateSeat(Exception):
    pass


class OrderNotFound(Exception):
    pass


class OrderNotPayable(Exception):
    def __init__(self, status: OrderStatus) -> None:
        self.status = status
        super().__init__(status.value)


class OrderService:
    def __init__(self, db: DbSession) -> None:
        self.db = db

    # -- disponibilidade ---------------------------------------------------

    def release_expired_holds(self) -> int:
        """Devolve ao estoque os assentos de pedidos que ninguém pagou.

        Roda antes de qualquer leitura ou escrita de disponibilidade, em vez de
        depender de tarefa agendada: sem processo de fundo no projeto, a
        limpeza precisa acontecer no caminho de quem usa. O custo é um UPDATE
        que quase sempre não encontra nada.
        """
        now = datetime.now(timezone.utc)

        vencidos = list(
            self.db.scalars(
                select(Order.id).where(
                    Order.status == OrderStatus.PENDING, Order.expires_at <= now
                )
            )
        )
        if not vencidos:
            return 0

        self.db.execute(
            update(Ticket)
            .where(Ticket.order_id.in_(vencidos))
            .values(status=TicketStatus.CANCELLED)
        )
        self.db.execute(
            update(Order).where(Order.id.in_(vencidos)).values(status=OrderStatus.EXPIRED)
        )
        self.db.commit()
        return len(vencidos)

    def taken_seats(self, session_id: uuid.UUID) -> set[tuple[uuid.UUID, str]]:
        self.release_expired_holds()
        linhas = self.db.execute(
            select(Ticket.sector_id, Ticket.seat_code).where(
                Ticket.session_id == session_id, Ticket.status.in_(OCCUPY_SEAT)
            )
        ).all()
        return {(sid, code) for sid, code in linhas}

    def session_on_sale(self, session_id: uuid.UUID) -> Session:
        session = self.db.get(Session, session_id)
        if (
            session is None
            or session.status is not SessionStatus.PUBLISHED
            or session.starts_at <= datetime.now(timezone.utc)
        ):
            raise SessionNotAvailable
        return session

    # -- compra ------------------------------------------------------------

    def create(self, customer_id: uuid.UUID, data: OrderCreate) -> Order:
        session = self.session_on_sale(data.session_id)

        chosen = [
            SeatSelection(sector_id=s.sector_id, seat_code=s.seat_code.strip().upper())
            for s in data.seats
        ]

        chaves = [(s.sector_id, s.seat_code) for s in chosen]
        if len(chaves) != len(set(chaves)):
            raise DuplicateSeat

        prices = {p.sector_id: p.price_cents for p in session.prices}
        sectors = {s.id: s for s in session.room.sectors}

        # A poltrona precisa existir na geometria e o setor precisa ser da sala
        # desta sessão. Sem isso, dava para comprar "Z99" e o pedido nasceria
        # válido para um lugar que não existe.
        unknown = [
            s.seat_code
            for s in chosen
            if s.sector_id not in sectors or not sectors[s.sector_id].has_seat(s.seat_code)
        ]
        if unknown:
            raise SeatDoesNotExist(unknown)

        occupied = self.taken_seats(session.id)
        taken = [s.seat_code for s in chosen if (s.sector_id, s.seat_code) in occupied]
        if taken:
            raise SeatTaken(taken)

        total = sum(prices[s.sector_id] for s in chosen)

        order = Order(customer_id=customer_id, session_id=session.id, total_cents=total)
        order.tickets = [
            Ticket(
                session_id=session.id,
                sector_id=s.sector_id,
                seat_code=s.seat_code,
                price_cents=prices[s.sector_id],
            )
            for s in chosen
        ]

        self.db.add(order)
        try:
            self.db.commit()
        except IntegrityError:
            # Duas compras simultâneas disputando a mesma poltrona: a checagem
            # acima passou nas duas, e o índice único parcial derrubou a
            # segunda. É o caminho normal sob concorrência, não um imprevisto.
            self.db.rollback()
            raise SeatTaken([s.seat_code for s in chosen])

        self.db.refresh(order)
        return order

    # -- pagamento ---------------------------------------------------------

    def pay(self, order_id: uuid.UUID, customer_id: uuid.UUID, card: dict) -> Order:
        order = self.get_for_customer(order_id, customer_id)

        if order.is_expired:
            self.release_expired_holds()
            self.db.refresh(order)

        if order.status is not OrderStatus.PENDING:
            raise OrderNotPayable(order.status)

        resultado = payment.process(card["card_number"], order.total_cents)

        if resultado.approved:
            order.status = OrderStatus.PAID
            order.paid_at = datetime.now(timezone.utc)
            for ticket in order.tickets:
                ticket.status = TicketStatus.VALID
        else:
            # Recusa devolve os assentos. Marcar CANCELLED basta: o índice
            # único parcial ignora esse estado, então a poltrona volta a ficar
            # livre sem nenhuma limpeza extra.
            order.status = OrderStatus.DECLINED
            order.decline_reason = resultado.reason
            for ticket in order.tickets:
                ticket.status = TicketStatus.CANCELLED

        self.db.commit()
        self.db.refresh(order)
        return order

    def cancel(self, order_id: uuid.UUID, customer_id: uuid.UUID) -> Order:
        order = self.get_for_customer(order_id, customer_id)
        if order.status not in (OrderStatus.PENDING, OrderStatus.PAID):
            raise OrderNotPayable(order.status)

        self._mark_cancelled(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def cancel_for_session(self, session_id: uuid.UUID) -> int:
        """Cancela todos os pedidos vivos de uma sessão. Devolve quantos.

        Quem chama é o organizador, pela sessão — o cliente não está por perto
        para consentir. Por isso cada pedido fica marcado como cancelado pelo
        organizador: é o que permite a tela do cliente dizer "o cinema
        cancelou" em vez de deixá-lo achar que a desistência foi dele.

        Ingresso já utilizado não é tocado, como no cancelamento comum: ele é
        registro de quem entrou. Ver decisão D30.
        """
        pedidos = list(
            self.db.scalars(
                select(Order).where(
                    Order.session_id == session_id,
                    Order.status.in_((OrderStatus.PENDING, OrderStatus.PAID)),
                )
            )
        )
        for order in pedidos:
            self._mark_cancelled(order, pelo_organizador=True)

        self.db.commit()
        return len(pedidos)

    @staticmethod
    def _mark_cancelled(order: Order, *, pelo_organizador: bool = False) -> None:
        """A regra de o que acontece com o pedido e os ingressos ao cancelar.

        Fica num lugar só porque os dois caminhos — o cliente desistindo e o
        organizador cancelando a sessão — precisam concordar sobre o que
        sobrevive. Não commita: quem chama decide o escopo da transação.
        """
        order.status = OrderStatus.CANCELLED
        order.cancelled_by_organizer = pelo_organizador
        for ticket in order.tickets:
            if ticket.status is not TicketStatus.USED:
                ticket.status = TicketStatus.CANCELLED

    # -- leitura -----------------------------------------------------------

    def get_for_customer(self, order_id: uuid.UUID, customer_id: uuid.UUID) -> Order:
        order = self.db.get(Order, order_id)
        if order is None or order.customer_id != customer_id:
            raise OrderNotFound
        return order

    def list_for_customer(self, customer_id: uuid.UUID) -> list[Order]:
        self.release_expired_holds()
        return list(
            self.db.scalars(
                select(Order)
                .where(Order.customer_id == customer_id)
                .order_by(Order.created_at.desc())
            )
        )

    def tickets_for_customer(self, customer_id: uuid.UUID) -> list[Ticket]:
        """Só ingressos que valem alguma coisa. Reserva não paga e ingresso
        cancelado não são documento, e poluiriam a carteira."""
        self.release_expired_holds()
        return list(
            self.db.scalars(
                select(Ticket)
                .join(Order)
                .where(
                    Order.customer_id == customer_id,
                    Ticket.status.in_((TicketStatus.VALID, TicketStatus.USED)),
                )
                .order_by(Ticket.created_at.desc())
            )
        )

    @staticmethod
    def code_for(ticket: Ticket) -> str | None:
        if ticket.status in (TicketStatus.VALID, TicketStatus.USED):
            return ticket_code.issue(ticket.id)
        return None
