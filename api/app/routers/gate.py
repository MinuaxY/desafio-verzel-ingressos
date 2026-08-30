"""Portaria e ingresso compartilhado."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.core.deps import require_role
from app.db import get_db
from app.models.user import Role, User
from app.schemas.order import (
    GateCheckIn,
    GateResultOut,
    TicketDetailOut,
    to_ticket_detail,
)
from app.schemas.session import SessionListItem, to_list_item
from app.services.gate_service import GateService
from app.services.order_service import OrderService
from app.services.session_service import SessionService

gate = APIRouter(
    prefix="/gate",
    tags=["Portaria"],
    dependencies=[Depends(require_role(Role.GATE))],
)


@gate.get("/sessions", response_model=list[SessionListItem])
def gate_sessions(db: DbSession = Depends(get_db)) -> list[SessionListItem]:
    """Sessões que a portaria pode estar conferindo agora.

    Endpoint próprio, e não a vitrine: a vitrine esconde o que já começou,
    porque quem compra não tem mais o que fazer ali. Na porta é o contrário —
    a sessão em andamento é justamente a que está recebendo gente.
    Ver decisão D33.
    """
    return [to_list_item(s) for s in SessionService(db).list_for_gate()]


@gate.post("/validate", response_model=GateResultOut)
def check(
    data: GateCheckIn,
    user: User = Depends(require_role(Role.GATE)),
    db: DbSession = Depends(get_db),
) -> GateResultOut:
    """Valida o ingresso na entrada.

    Responde sempre 200, com o veredito no corpo. Códigos de erro HTTP diriam
    que a requisição falhou, e não é o caso: "este ingresso já foi usado" é uma
    resposta bem-sucedida a uma pergunta legítima, e a tela precisa dela para
    mostrar o resultado em vez de um erro.
    """
    resultado = GateService(db).check(
        data.code, operador_id=user.id, session_id=data.session_id
    )

    ticket = None
    if resultado.ticket is not None:
        ticket = to_ticket_detail(
            resultado.ticket, code=OrderService.code_for(resultado.ticket)
        )

    return GateResultOut(
        result=resultado.result,
        message=resultado.message,
        ticket=ticket,
        used_at=resultado.used_at,
    )


# --------------------------------------------------------------------------
# Ingresso compartilhado por link (publico)
# --------------------------------------------------------------------------

compartilhado = APIRouter(prefix="/shared", tags=["Ingresso compartilhado"])


@compartilhado.get("/{share_token}", response_model=TicketDetailOut)
def shared_ticket(share_token: uuid.UUID, db: DbSession = Depends(get_db)) -> TicketDetailOut:
    """Abre um ingresso por link, sem exigir conta.

    Quem tem o link consegue entrar com o ingresso, e é assim que precisa ser:
    comprar três lugares e mandar um para cada amigo é o caso de uso. Um link
    que não deixasse a pessoa passar na portaria não serviria para nada.

    O token na URL é opaco e diferente do código assinado, que vai no corpo da
    resposta — assim o código de entrada não fica registrado em histórico de
    navegador nem em log de servidor. Ver decisão D17.
    """
    ticket = GateService(db).by_share_token(share_token)
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingresso não encontrado")
    return to_ticket_detail(ticket, code=OrderService.code_for(ticket))
