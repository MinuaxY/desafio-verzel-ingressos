"""Agrega os models para que o Alembic enxergue todas as tabelas."""
from app.models.order import (  # noqa: F401
    MINUTOS_PARA_PAGAR,
    OCUPAM_ASSENTO,
    Order,
    OrderStatus,
    Ticket,
    TicketStatus,
)
from app.models.room import (  # noqa: F401
    MAX_FILEIRAS,
    MAX_POLTRONAS_POR_FILEIRA,
    Room,
    SeatAttribute,
    SeatKind,
    Sector,
)
from app.models.session import (  # noqa: F401
    AudioType,
    ScreenFormat,
    Session,
    SessionSectorPrice,
    SessionStatus,
)
from app.models.user import Role, User  # noqa: F401

__all__ = [
    "MAX_FILEIRAS",
    "MAX_POLTRONAS_POR_FILEIRA",
    "MINUTOS_PARA_PAGAR",
    "OCUPAM_ASSENTO",
    "Order",
    "OrderStatus",
    "AudioType",
    "Role",
    "ScreenFormat",
    "Room",
    "SeatAttribute",
    "SeatKind",
    "Sector",
    "Session",
    "SessionSectorPrice",
    "SessionStatus",
    "Ticket",
    "TicketStatus",
    "User",
]
