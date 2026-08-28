"""Regra de negócio da autenticação."""
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import Role, User
from app.repositories.user_repository import UserRepository
from app.schemas.user import TokenOut, UserLogin, UserOut, UserRegister


class EmailAlreadyUsed(Exception):
    pass


class InvalidCredentials(Exception):
    pass


class AuthService:
    def __init__(self, db: Session) -> None:
        self.users = UserRepository(db)

    def register(self, data: UserRegister) -> TokenOut:
        if self.users.get_by_email(data.email):
            raise EmailAlreadyUsed
        user = self.users.create(
            name=data.name,
            email=data.email,
            password_hash=hash_password(data.password),
            # Fixo, e não vindo do pedido: era daqui que saía a escalada de
            # privilégio. Ver decisão D34.
            role=Role.CUSTOMER,
        )
        return self._token_for(user)

    def login(self, data: UserLogin) -> TokenOut:
        user = self.users.get_by_email(data.email)
        # Mesma exceção para e-mail inexistente e senha errada: não entregamos
        # a quem tenta adivinhar a informação de quais e-mails existem.
        if not user or not verify_password(data.password, user.password_hash):
            raise InvalidCredentials
        return self._token_for(user)

    @staticmethod
    def _token_for(user: User) -> TokenOut:
        token = create_access_token(subject=str(user.id), role=user.role.value)
        return TokenOut(access_token=token, user=UserOut.model_validate(user))
