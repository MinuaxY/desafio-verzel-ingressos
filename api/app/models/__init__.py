"""Agrega os models para que o Alembic enxergue todas as tabelas."""
from app.models.order import (  # noqa: F401
    MINUTES_TO_PAY,
    OCCUPY_SEAT,
    Order,
    OrderStatus,
    Ticket,
    TicketStatus,
)
from app.models.room import (  # noqa: F401
    MAX_ROWS,
    MAX_SEATS_PER_ROW,
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
