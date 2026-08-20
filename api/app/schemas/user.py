"""Contratos de entrada e saída da autenticação."""
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import Role


class UserRegister(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)  # 72 é o limite do bcrypt
    role: Role = Role.CUSTOMER


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
