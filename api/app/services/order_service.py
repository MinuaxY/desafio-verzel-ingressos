"""Compra de ingressos: reserva, pagamento e emissão."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from app.core import ticket_code
from app.models.order import OCUPAM_ASSENTO, Order, OrderStatus, Ticket, TicketStatus
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

    def liberar_reservas_vencidas(self) -> int:
        """Devolve ao estoque os assentos de pedidos que ninguém pagou.

        Roda antes de qualquer leitura ou escrita de disponibilidade, em vez de
        depender de tarefa agendada: sem processo de fundo no projeto, a
        limpeza precisa acontecer no caminho de quem usa. O custo é um UPDATE
        que quase sempre não encontra nada.
        """
        agora = datetime.now(timezone.utc)

        vencidos = list(
            self.db.scalars(
                select(Order.id).where(
                    Order.status == OrderStatus.PENDING, Order.expires_at <= agora
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

    def assentos_ocupados(self, session_id: uuid.UUID) -> set[tuple[uuid.UUID, str]]:
        self.liberar_reservas_vencidas()
        linhas = self.db.execute(
            select(Ticket.sector_id, Ticket.seat_code).where(
                Ticket.session_id == session_id, Ticket.status.in_(OCUPAM_ASSENTO)
            )
        ).all()
        return {(sid, code) for sid, code in linhas}

    def sessao_a_venda(self, session_id: uuid.UUID) -> Session:
        sessao = self.db.get(Session, session_id)
        if (
            sessao is None
            or sessao.status is not SessionStatus.PUBLISHED
            or sessao.starts_at <= datetime.now(timezone.utc)
        ):
            raise SessionNotAvailable
        return sessao

    # -- compra ------------------------------------------------------------

    def criar(self, customer_id: uuid.UUID, dados: OrderCreate) -> Order:
        sessao = self.sessao_a_venda(dados.session_id)

        escolhidos = [
            SeatSelection(sector_id=s.sector_id, seat_code=s.seat_code.strip().upper())
            for s in dados.seats
        ]

        chaves = [(s.sector_id, s.seat_code) for s in escolhidos]
        if len(chaves) != len(set(chaves)):
            raise DuplicateSeat

        precos = {p.sector_id: p.price_cents for p in sessao.prices}
        setores = {s.id: s for s in sessao.room.sectors}

        # A poltrona precisa existir na geometria e o setor precisa ser da sala
        # desta sessão. Sem isso, dava para comprar "Z99" e o pedido nasceria
        # válido para um lugar que não existe.
        inexistentes = [
            s.seat_code
            for s in escolhidos
            if s.sector_id not in setores or not setores[s.sector_id].has_seat(s.seat_code)
        ]
        if inexistentes:
            raise SeatDoesNotExist(inexistentes)

        ocupados = self.assentos_ocupados(sessao.id)
        tomados = [s.seat_code for s in escolhidos if (s.sector_id, s.seat_code) in ocupados]
        if tomados:
            raise SeatTaken(tomados)

        total = sum(precos[s.sector_id] for s in escolhidos)

        pedido = Order(customer_id=customer_id, session_id=sessao.id, total_cents=total)
        pedido.tickets = [
            Ticket(
                session_id=sessao.id,
                sector_id=s.sector_id,
                seat_code=s.seat_code,
                price_cents=precos[s.sector_id],
            )
            for s in escolhidos
        ]

        self.db.add(pedido)
        try:
            self.db.commit()
        except IntegrityError:
            # Duas compras simultâneas disputando a mesma poltrona: a checagem
            # acima passou nas duas, e o índice único parcial derrubou a
            # segunda. É o caminho normal sob concorrência, não um imprevisto.
            self.db.rollback()
            raise SeatTaken([s.seat_code for s in escolhidos])

        self.db.refresh(pedido)
        return pedido

    # -- pagamento ---------------------------------------------------------

    def pagar(self, order_id: uuid.UUID, customer_id: uuid.UUID, card: dict) -> Order:
        pedido = self.obter(order_id, customer_id)

        if pedido.is_expired:
            self.liberar_reservas_vencidas()
            self.db.refresh(pedido)

        if pedido.status is not OrderStatus.PENDING:
            raise OrderNotPayable(pedido.status)

        resultado = payment.processar(card["card_number"], pedido.total_cents)

        if resultado.aprovado:
            pedido.status = OrderStatus.PAID
            pedido.paid_at = datetime.now(timezone.utc)
            for ingresso in pedido.tickets:
                ingresso.status = TicketStatus.VALID
        else:
            # Recusa devolve os assentos. Marcar CANCELLED basta: o índice
            # único parcial ignora esse estado, então a poltrona volta a ficar
            # livre sem nenhuma limpeza extra.
            pedido.status = OrderStatus.DECLINED
            pedido.decline_reason = resultado.motivo
            for ingresso in pedido.tickets:
                ingresso.status = TicketStatus.CANCELLED

        self.db.commit()
        self.db.refresh(pedido)
        return pedido

    def cancelar(self, order_id: uuid.UUID, customer_id: uuid.UUID) -> Order:
        pedido = self.obter(order_id, customer_id)
        if pedido.status not in (OrderStatus.PENDING, OrderStatus.PAID):
            raise OrderNotPayable(pedido.status)

        self._marca_cancelado(pedido)
        self.db.commit()
        self.db.refresh(pedido)
        return pedido

    def cancelar_da_sessao(self, session_id: uuid.UUID) -> int:
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
        for pedido in pedidos:
            self._marca_cancelado(pedido, pelo_organizador=True)

        self.db.commit()
        return len(pedidos)

    @staticmethod
    def _marca_cancelado(pedido: Order, *, pelo_organizador: bool = False) -> None:
        """A regra de o que acontece com o pedido e os ingressos ao cancelar.

        Fica num lugar só porque os dois caminhos — o cliente desistindo e o
        organizador cancelando a sessão — precisam concordar sobre o que
        sobrevive. Não commita: quem chama decide o escopo da transação.
        """
        pedido.status = OrderStatus.CANCELLED
        pedido.cancelled_by_organizer = pelo_organizador
        for ingresso in pedido.tickets:
            if ingresso.status is not TicketStatus.USED:
                ingresso.status = TicketStatus.CANCELLED

    # -- leitura -----------------------------------------------------------

    def obter(self, order_id: uuid.UUID, customer_id: uuid.UUID) -> Order:
        pedido = self.db.get(Order, order_id)
        if pedido is None or pedido.customer_id != customer_id:
            raise OrderNotFound
        return pedido

    def listar_do_cliente(self, customer_id: uuid.UUID) -> list[Order]:
        self.liberar_reservas_vencidas()
        return list(
            self.db.scalars(
                select(Order)
                .where(Order.customer_id == customer_id)
                .order_by(Order.created_at.desc())
            )
        )

    def ingressos_do_cliente(self, customer_id: uuid.UUID) -> list[Ticket]:
        """Só ingressos que valem alguma coisa. Reserva não paga e ingresso
        cancelado não são documento, e poluiriam a carteira."""
        self.liberar_reservas_vencidas()
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
    def codigo_do(ingresso: Ticket) -> str | None:
        if ingresso.status in (TicketStatus.VALID, TicketStatus.USED):
            return ticket_code.gerar(ingresso.id)
        return None
