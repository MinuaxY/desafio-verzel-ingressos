"""Acesso a dados de sessão. Sem regra de negócio."""
import uuid
from datetime import date, datetime

from sqlalchemy import Date, Select, cast, func, or_, select
from sqlalchemy.orm import Session as DbSession

from app.models.session import Session, SessionSectorPrice, SessionStatus

# O fuso em que as datas são apresentadas e filtradas. Sessão de cinema é hora
# local: quem procura "sexta" quer a noite de sexta na cidade, não o intervalo
# UTC correspondente.
DISPLAY_TIMEZONE = "America/Sao_Paulo"


class SessionRepository:
    def __init__(self, db: DbSession) -> None:
        self.db = db

    def get(self, session_id: uuid.UUID) -> Session | None:
        return self.db.get(Session, session_id)

    def _filtrar(
        self,
        query: Select,
        *,
        search: str | None,
        from_time: datetime | None,
        day: date | None = None,
        timezone: str = DISPLAY_TIMEZONE,
    ) -> Select:
        if search:
            term = f"%{search.strip()}%"
            query = query.where(
                or_(Session.movie_title.ilike(term), Session.movie_overview.ilike(term))
            )
        if from_time:
            query = query.where(Session.starts_at >= from_time)
        if day:
            # A comparação é feita no fuso de exibição, não em UTC. Uma sessão
            # de sexta às 21h30 em São Paulo é sábado 00h30 em UTC — filtrar
            # pela data crua colocaria ela no dia errado para quem procura.
            query = query.where(
                cast(func.timezone(timezone, Session.starts_at), Date) == day
            )
        return query

    def list_published(
        self,
        *,
        search: str | None = None,
        from_time: datetime | None = None,
        day: date | None = None,
        page: int = 1,
        per_page: int = 12,
    ) -> tuple[list[Session], int]:
        base = select(Session).where(Session.status == SessionStatus.PUBLISHED)
        base = self._filtrar(base, search=search, from_time=from_time, day=day)

        total = self.db.scalar(select(func.count()).select_from(base.subquery())) or 0

        items = list(
            self.db.scalars(
                base.order_by(Session.starts_at).offset((page - 1) * per_page).limit(per_page)
            )
        )
        return items, total

    def days_with_sessions(
        self, *, from_time: datetime, until: datetime, search: str | None = None
    ) -> dict[date, int]:
        """Quantas sessões há em cada dia, para a barra de datas da vitrine.

        Uma consulta agregada em vez de uma por dia: a barra mostra duas
        semanas, e catorze idas ao banco para desenhar um filtro seria caro
        para o que a informação vale.
        """
        column = cast(func.timezone(DISPLAY_TIMEZONE, Session.starts_at), Date)

        query = (
            select(column.label("day"), func.count().label("total"))
            .where(
                Session.status == SessionStatus.PUBLISHED,
                Session.starts_at >= from_time,
                Session.starts_at < until,
            )
            .group_by(column)
        )
        if search:
            term = f"%{search.strip()}%"
            query = query.where(
                or_(Session.movie_title.ilike(term), Session.movie_overview.ilike(term))
            )

        return {row.day: row.total for row in self.db.execute(query)}

    def list_by_organizer(self, organizer_id: uuid.UUID) -> list[Session]:
        return list(
            self.db.scalars(
                select(Session)
                .where(Session.organizer_id == organizer_id)
                .order_by(Session.starts_at.desc())
            )
        )

    def overlaps(
        self,
        room_id: uuid.UUID,
        starts_at: datetime,
        occupies_until: datetime,
        *,
        ignoring: uuid.UUID | None = None,
    ) -> bool:
        """A sala já está ocupada em alguma parte desse intervalo?

        Substituiu uma comparação por igualdade de horário, que só pegava duas
        sessões começando no mesmo instante: às 20:00 e às 20:01 dois filmes de
        duas horas passavam, e a sala ficava com duas plateias.

        Sessão cancelada não conta — ela não vai acontecer, então não ocupa
        nada. Mesma regra da D31.

        `ignoring` serve para a edição: ao mudar o horário de uma sessão, ela
        não pode conflitar consigo mesma. Ver decisão D37.
        """
        condicoes = [
            Session.room_id == room_id,
            Session.status != SessionStatus.CANCELLED,
            # Sobreposição de intervalos: começa antes de o outro acabar e
            # acaba depois de o outro começar. Encostar não é sobrepor — uma
            # sessão pode começar exatamente quando a sala é liberada.
            Session.starts_at < occupies_until,
            Session.occupies_until > starts_at,
        ]
        if ignoring is not None:
            condicoes.append(Session.id != ignoring)

        return self.db.scalar(select(Session.id).where(*condicoes).limit(1)) is not None

    def create(self, session: Session, prices: list[SessionSectorPrice]) -> Session:
        session.prices = prices
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def save(self, session: Session) -> Session:
        self.db.commit()
        self.db.refresh(session)
        return session
