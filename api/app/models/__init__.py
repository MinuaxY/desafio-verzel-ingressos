"""Agrega os models para que o Alembic enxergue todas as tabelas."""
from app.models.user import Role, User  # noqa: F401

__all__ = ["Role", "User"]
