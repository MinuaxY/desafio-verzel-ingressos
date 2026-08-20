"""Acesso a dados de usuário. Sem regra de negócio."""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import Role, User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email.lower()))

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.db.get(User, user_id)

    def create(self, *, name: str, email: str, password_hash: str, role: Role) -> User:
        user = User(name=name, email=email.lower(), password_hash=password_hash, role=role)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
