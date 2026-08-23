"""Acesso a dados de sessão. Sem regra de negócio."""
import uuid
from datetime import date, datetime

from sqlalchemy import Date, Select, cast, func, or_, select
from sqlalchemy.orm import Session as DbSession

from app.models.session import Session, SessionSectorPrice, SessionStatus

# O fuso em que as datas são apresentadas e filtradas. Sessão de cinema é hora
# local: quem procura "sexta" quer a noite de sexta na cidade, não o intervalo
# UTC correspondente.
FUSO_EXIBICAO = "America/Sao_Paulo"


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
        dia: date | None = None,
        fuso: str = FUSO_EXIBICAO,
    ) -> Select:
        if busca:
            termo = f"%{busca.strip()}%"
            consulta = consulta.where(
                or_(Session.movie_title.ilike(termo), Session.movie_overview.ilike(termo))
            )
        if a_partir_de:
            consulta = consulta.where(Session.starts_at >= a_partir_de)
        if dia:
            # A comparação é feita no fuso de exibição, não em UTC. Uma sessão
            # de sexta às 21h30 em São Paulo é sábado 00h30 em UTC — filtrar
            # pela data crua colocaria ela no dia errado para quem procura.
            consulta = consulta.where(
                cast(func.timezone(fuso, Session.starts_at), Date) == dia
            )
        return consulta

    def list_published(
        self,
        *,
        busca: str | None = None,
        a_partir_de: datetime | None = None,
        dia: date | None = None,
        page: int = 1,
        por_pagina: int = 12,
    ) -> tuple[list[Session], int]:
        base = select(Session).where(Session.status == SessionStatus.PUBLISHED)
        base = self._filtrar(base, busca=busca, a_partir_de=a_partir_de, dia=dia)

        total = self.db.scalar(select(func.count()).select_from(base.subquery())) or 0

        itens = list(
            self.db.scalars(
                base.order_by(Session.starts_at).offset((page - 1) * por_pagina).limit(por_pagina)
            )
        )
        return itens, total

    def dias_com_sessao(
        self, *, a_partir_de: datetime, ate: datetime, busca: str | None = None
    ) -> dict[date, int]:
        """Quantas sessões há em cada dia, para a barra de datas da vitrine.

        Uma consulta agregada em vez de uma por dia: a barra mostra duas
        semanas, e catorze idas ao banco para desenhar um filtro seria caro
        para o que a informação vale.
        """
        coluna = cast(func.timezone(FUSO_EXIBICAO, Session.starts_at), Date)

        consulta = (
            select(coluna.label("dia"), func.count().label("total"))
            .where(
                Session.status == SessionStatus.PUBLISHED,
                Session.starts_at >= a_partir_de,
                Session.starts_at < ate,
            )
            .group_by(coluna)
        )
        if busca:
            termo = f"%{busca.strip()}%"
            consulta = consulta.where(
                or_(Session.movie_title.ilike(termo), Session.movie_overview.ilike(termo))
            )

        return {linha.dia: linha.total for linha in self.db.execute(consulta)}

    def list_by_organizer(self, organizer_id: uuid.UUID) -> list[Session]:
        return list(
            self.db.scalars(
                select(Session)
                .where(Session.organizer_id == organizer_id)
                .order_by(Session.starts_at.desc())
            )
        )

    def exists_at(self, room_id: uuid.UUID, starts_at: datetime) -> bool:
        """A sala está ocupada nesse horário?

        Sessão cancelada **não** ocupa. A pergunta não é "existe alguma linha",
        e sim "existe alguma sessão que vai acontecer" — e cancelada é
        justamente o anúncio de que não vai. Contá-la deixaria o horário preso
        para sempre, já que cancelar não tem volta.

        É a mesma regra do índice parcial que impede vender a poltrona duas
        vezes: cancelado não ocupa. Ver decisão D31.
        """
        return (
            self.db.scalar(
                select(Session.id).where(
                    Session.room_id == room_id,
                    Session.starts_at == starts_at,
                    Session.status != SessionStatus.CANCELLED,
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
