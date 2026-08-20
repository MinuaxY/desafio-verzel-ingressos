"""Acesso a dados de sessão. Sem regra de negócio."""
import uuid
from datetime import datetime

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session as DbSession

from app.models.session import Session, SessionSectorPrice, SessionStatus


class SessionRepository:
    def __init__(self, db: DbSession) -> None:
        self.db = db

    def get(self, session_id: uuid.UUID) -> Session | None:
        return self.db.get(Session, session_id)

    def _filtrar(
        self,
        consulta: Select,
        *,
        busca: str | None,
        a_partir_de: datetime | None,
    ) -> Select:
        if busca:
            termo = f"%{busca.strip()}%"
            consulta = consulta.where(
                or_(Session.movie_title.ilike(termo), Session.movie_overview.ilike(termo))
            )
        if a_partir_de:
            consulta = consulta.where(Session.starts_at >= a_partir_de)
        return consulta

    def list_published(
        self,
        *,
        busca: str | None = None,
        a_partir_de: datetime | None = None,
        page: int = 1,
        por_pagina: int = 12,
    ) -> tuple[list[Session], int]:
        base = select(Session).where(Session.status == SessionStatus.PUBLISHED)
        base = self._filtrar(base, busca=busca, a_partir_de=a_partir_de)

        total = self.db.scalar(select(func.count()).select_from(base.subquery())) or 0

        itens = list(
            self.db.scalars(
                base.order_by(Session.starts_at).offset((page - 1) * por_pagina).limit(por_pagina)
            )
        )
        return itens, total

    def list_by_organizer(self, organizer_id: uuid.UUID) -> list[Session]:
        return list(
            self.db.scalars(
                select(Session)
                .where(Session.organizer_id == organizer_id)
                .order_by(Session.starts_at.desc())
            )
        )

    def exists_at(self, room_id: uuid.UUID, starts_at: datetime) -> bool:
        return (
            self.db.scalar(
                select(Session.id).where(
                    Session.room_id == room_id, Session.starts_at == starts_at
                )
            )
            is not None
        )

    def create(self, sessao: Session, precos: list[SessionSectorPrice]) -> Session:
        sessao.prices = precos
        self.db.add(sessao)
        self.db.commit()
        self.db.refresh(sessao)
        return sessao

    def save(self, sessao: Session) -> Session:
        self.db.commit()
        self.db.refresh(sessao)
        return sessao
