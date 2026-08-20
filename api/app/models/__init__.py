"""Agrega os models para que o Alembic enxergue todas as tabelas."""
from app.models.room import MAX_FILEIRAS, MAX_POLTRONAS_POR_FILEIRA, Room, Sector  # noqa: F401
from app.models.session import Session, SessionSectorPrice, SessionStatus  # noqa: F401
from app.models.user import Role, User  # noqa: F401

__all__ = [
    "MAX_FILEIRAS",
    "MAX_POLTRONAS_POR_FILEIRA",
    "Role",
    "Room",
    "Sector",
    "Session",
    "SessionSectorPrice",
    "SessionStatus",
    "User",
]
