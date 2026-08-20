"""Endpoints de autenticação."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db import get_db
from app.models.user import Role, User
from app.schemas.user import TokenOut, UserLogin, UserOut, UserRegister
from app.services.auth_service import AuthService, EmailAlreadyUsed, InvalidCredentials

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(data: UserRegister, db: Session = Depends(get_db)) -> TokenOut:
    try:
        return AuthService(db).register(data)
    except EmailAlreadyUsed:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este e-mail já está cadastrado")


@router.post("/login", response_model=TokenOut)
def login(data: UserLogin, db: Session = Depends(get_db)) -> TokenOut:
    try:
        return AuthService(db).login(data)
    except InvalidCredentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou senha inválidos")


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.get("/organizer-only", include_in_schema=False)
def organizer_only(user: User = Depends(require_role(Role.ORGANIZER))) -> dict[str, str]:
    """Rota de verificação da autorização por papel (T6). Removida na Sprint 2,
    quando os endpoints reais de organizador passarem a exercer a mesma trava."""
    return {"ok": user.email}
