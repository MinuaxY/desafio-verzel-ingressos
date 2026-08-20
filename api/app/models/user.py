"""Usuário e seus papéis."""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum as SAEnum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Role(str, enum.Enum):
    """Os três papéis do sistema.

    ORGANIZER cria e gerencia sessões. CUSTOMER reserva, paga e recebe
    ingressos. GATE valida ingressos na entrada e não faz mais nada.
    """

    ORGANIZER = "ORGANIZER"
    CUSTOMER = "CUSTOMER"
    GATE = "GATE"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(SAEnum(Role, name="user_role"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.email} {self.role.value}>"
