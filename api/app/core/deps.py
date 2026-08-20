"""Dependências de autenticação e autorização."""
import uuid
from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db import get_db
from app.models.user import Role, User
from app.repositories.user_repository import UserRepository

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Autenticação necessária")

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido ou expirado")

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token malformado")

    user = UserRepository(db).get_by_id(user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuário não encontrado")
    return user


def require_role(*allowed: Role) -> Callable[..., User]:
    """Restringe uma rota aos papéis informados.

    Uso: `Depends(require_role(Role.ORGANIZER))`. Responde 403 quando o usuário
    está autenticado mas o papel não permite a operação — distinto do 401, que
    significa não sabemos quem é.
    """

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            permitidos = ", ".join(r.value for r in allowed)
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Acesso restrito ao papel: {permitidos}",
            )
        return user

    return dependency
