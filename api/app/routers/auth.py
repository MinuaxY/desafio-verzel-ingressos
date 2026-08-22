"""Endpoints de autenticação."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.core.throttle import tentativas_de_login
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
def login(data: UserLogin, request: Request, db: Session = Depends(get_db)) -> TokenOut:
    # A chave junta IP e e-mail: só por IP puniria uma rede compartilhada
    # inteira, e só por e-mail deixaria alguém bloquear a conta de outra
    # pessoa de propósito. Ver decisão D26.
    origem = request.client.host if request.client else "desconhecido"
    chave = f"{origem}|{data.email.lower()}"

    if (espera := tentativas_de_login.bloqueado(chave)):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Muitas tentativas. Tente de novo em {espera} segundos.",
            headers={"Retry-After": str(espera)},
        )

    try:
        resposta = AuthService(db).login(data)
    except InvalidCredentials:
        tentativas_de_login.registrar(chave)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou senha inválidos")

    # Quem acertou não carrega o histórico de erros para a próxima vez.
    tentativas_de_login.liberar(chave)
    return resposta


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.get("/organizer-only", include_in_schema=False)
def organizer_only(user: User = Depends(require_role(Role.ORGANIZER))) -> dict[str, str]:
    """Rota de verificação da autorização por papel (T6). Removida na Sprint 2,
    quando os endpoints reais de organizador passarem a exercer a mesma trava."""
    return {"ok": user.email}
