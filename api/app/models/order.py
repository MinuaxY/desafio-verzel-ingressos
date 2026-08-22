"""Pedidos e ingressos.

O pedido agrupa a compra; cada assento vira um ingresso. O pagamento é
simulado, mas o ciclo é o de verdade: o pedido nasce pendente, os assentos
ficam presos enquanto ele vive, e só viram ingresso válido quando o pagamento
é aprovado. Recusa devolve os assentos.
"""
import enum
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

# Quanto tempo os assentos ficam presos esperando o pagamento. Sem isso, um
# cliente que abandona o checkout travaria a poltrona para sempre.
MINUTOS_PARA_PAGAR = 15


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"    # aguardando pagamento; assentos presos
    PAID = "PAID"          # pago; ingressos emitidos
    DECLINED = "DECLINED"  # pagamento recusado; assentos devolvidos
    EXPIRED = "EXPIRED"    # cliente não pagou a tempo; assentos devolvidos
    CANCELLED = "CANCELLED"


class TicketStatus(str, enum.Enum):
    RESERVED = "RESERVED"    # o pedido ainda não foi pago
    VALID = "VALID"          # pago, vale entrada
    USED = "USED"            # já passou pela portaria
    CANCELLED = "CANCELLED"  # pedido recusado, expirado ou cancelado


# Estados em que o ingresso ainda ocupa a poltrona. CANCELLED não ocupa — é
# exatamente o que o índice único parcial ignora.
OCUPAM_ASSENTO = (TicketStatus.RESERVED, TicketStatus.VALID, TicketStatus.USED)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )

    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus, name="order_status"), default=OrderStatus.PENDING, index=True
    )
    total_cents: Mapped[int] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc) + timedelta(minutes=MINUTOS_PARA_PAGAR),
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    # Motivo da recusa, para a tela conseguir explicar o que aconteceu.
    decline_reason: Mapped[str | None] = mapped_column(String(120), default=None)

    session: Mapped["Session"] = relationship(lazy="selectin")  # noqa: F821
    tickets: Mapped[list["Ticket"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (CheckConstraint("total_cents >= 0", name="ck_pedido_total"),)

    @property
    def is_expired(self) -> bool:
        return self.status is OrderStatus.PENDING and self.expires_at <= datetime.now(timezone.utc)


class Ticket(Base):
    """Um assento comprado.

    O `code` é o que vai no QR, e carrega assinatura: sem o segredo do servidor
    não dá para forjar um código que a portaria aceite. Ver decisão D6.

    O `share_token` é separado do `code`, e não é uma segunda camada de
    proteção: quem abre o link enxerga o QR e consegue entrar com ele. Isso é
    intencional — comprar três ingressos e mandar um para cada amigo é o caso
    de uso, e ingresso encaminhado precisa funcionar na portaria.

    A separação existe para que o código de entrada não trafegue na URL, onde
    ficaria registrado em histórico de navegador, log de servidor e cabeçalho
    de origem. O token é opaco e descartável; o código assinado fica no corpo
    da resposta. Ver decisão D17.
    """

    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    sector_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sectors.id"))

    seat_code: Mapped[str] = mapped_column(String(4))
    price_cents: Mapped[int] = mapped_column(Integer)

    status: Mapped[TicketStatus] = mapped_column(
        SAEnum(TicketStatus, name="ticket_status"), default=TicketStatus.RESERVED, index=True
    )

    share_token: Mapped[uuid.UUID] = mapped_column(default=uuid.uuid4, unique=True, index=True)

    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    used_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    order: Mapped["Order"] = relationship(back_populates="tickets")
    session: Mapped["Session"] = relationship(lazy="selectin")  # noqa: F821
    sector: Mapped["Sector"] = relationship(lazy="selectin")  # noqa: F821

    __table_args__ = (
        # O coração da garantia de não vender duas vezes.
        #
        # Índice único PARCIAL: a mesma poltrona da mesma sessão só pode ter um
        # ingresso que não esteja cancelado. O banco recusa a segunda venda por
        # definição, sem lock explícito e sem lógica de concorrência na
        # aplicação. Pagamento recusado marca CANCELLED e a poltrona volta a
        # ficar livre, sem nenhum trabalho extra. Ver decisões D5 e D15.
        Index(
            "uq_assento_por_sessao",
            "session_id",
            "sector_id",
            "seat_code",
            unique=True,
            postgresql_where=(status != TicketStatus.CANCELLED),
        ),
        UniqueConstraint("share_token", name="uq_ingresso_share_token"),
        CheckConstraint("price_cents >= 0", name="ck_ingresso_preco"),
    )
