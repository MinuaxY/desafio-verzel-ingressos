"""Contratos de entrada e saída da autenticação."""
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import Role


class UserRegister(BaseModel):
    """Cadastro público. Cria sempre um cliente.

    O papel **não** é campo de entrada. Enviá-lo devolve 422 em vez de ser
    ignorado em silêncio: um campo de segurança que a API descarta sem avisar
    ensina o cliente a acreditar que pediu algo que nunca foi concedido.

    Organizador e portaria vêm do fluxo administrativo (`python -m app.admin`),
    não daqui. Ver decisão D34.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)  # 72 é o limite do bcrypt


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: EmailStr
    role: Role


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
