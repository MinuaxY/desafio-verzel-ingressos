"""Regra de negócio das sessões."""
import uuid
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.catalog.factory import get_catalog_provider
from app.models.order import OCCUPY_SEAT, Ticket
from app.models.session import (
    Session,
    SessionSectorPrice,
    SessionStatus,
    occupation_end,
)
from app.repositories.room_repository import RoomRepository
from app.repositories.session_repository import SessionRepository
from app.schemas.session import SessionCreate, SessionRepeat, SessionUpdate
from app.services.order_service import OrderService
from app.services.room_service import RoomNotFound, RoomService

# "Dia 24 às 19h" é hora local de quem vai ao cinema. Ver decisão D27.
LOCAL_TIMEZONE = ZoneInfo("America/Sao_Paulo")

# A sessão continua na lista da portaria depois de começar: público atrasado
# ainda está entrando. Ver decisão D33.
GATE_GRACE_PERIOD = timedelta(hours=6)

# Sem teto, um engano na seleção criaria centenas de sessões.
MAX_BATCH_DATES = 60


class MovieNotFound(Exception):
    pass


class SessionNotFound(Exception):
    pass


class RoomBusy(Exception):
    """A sala já está ocupada em alguma parte desse intervalo.

    Não é colisão de horário de início: uma sessão reserva a sala pelo tempo do
    filme mais a folga de limpeza. Ver decisão D37.
    """


class SessionInThePast(Exception):
    pass


class PricesDoNotCoverSectors(Exception):
    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        super().__init__(f"Sem preço para: {', '.join(missing)}")


class SessionAlreadyCancelled(Exception):
    pass


class SessionHasTickets(Exception):
    """A sessão já vendeu ingresso: não pode ser apagada nem ter o horário
    mudado por baixo de quem comprou."""


class SessionSold(Exception):
    """A sessão já vendeu: cancelar exige resolver com quem comprou antes."""

    def __init__(self, sold: int) -> None:
        self.sold = sold
        super().__init__(f"{sold} ingresso(s) vendido(s)")


class SessionIsPublished(Exception):
    """Sessão publicada sai do cartaz com despublicar, não com exclusão."""


class SessionService:
    def __init__(self, db: DbSession) -> None:
        self.db = db
        self.sessions = SessionRepository(db)
        self.rooms = RoomRepository(db)
        self.room_service = RoomService(db)

    # -- leitura pública ---------------------------------------------------

    def list_public(
        self,
        *,
        search: str | None = None,
        day: date | None = None,
        include_past: bool = False,
        page: int = 1,
        per_page: int = 12,
    ) -> tuple[list[Session], int]:
        # Sessão que já começou não interessa a quem quer comprar.
        corte = None if include_past else datetime.now(timezone.utc)
        return self.sessions.list_published(
            search=search, from_time=corte, day=day, page=page, per_page=per_page
        )

    def days_on_billboard(self, *, days: int = 14, search: str | None = None) -> dict[date, int]:
        """Quantas sessões há em cada dia, para a barra de datas saber quais
        dias oferecer como clicáveis."""
        now = datetime.now(timezone.utc)
        fim = datetime.combine(
            now.astimezone(LOCAL_TIMEZONE).date() + timedelta(days=days),
            time.min,
            tzinfo=LOCAL_TIMEZONE,
        )
        return self.sessions.days_with_sessions(from_time=now, until=fim, search=search)

    def list_for_gate(self) -> list[Session]:
        """Sessões do turno da portaria: da que está em andamento às próximas.

        A vitrine esconde o que já começou, o que está certo para quem compra e
        errado para quem está na porta. Ver decisão D33.
        """
        now = datetime.now(timezone.utc)
        items, _ = self.sessions.list_published(
            from_time=now - GATE_GRACE_PERIOD,
            page=1,
            per_page=100,
        )
        return [s for s in items if s.starts_at <= now + timedelta(days=2)]

    def get_public(self, session_id: uuid.UUID) -> Session:
        session = self.sessions.get(session_id)
        if session is None or not session.is_public:
            raise SessionNotFound
        return session

    # -- leitura do organizador -------------------------------------------

    def list_for_organizer(self, organizer_id: uuid.UUID) -> list[Session]:
        return self.sessions.list_by_organizer(organizer_id)

    def get_for_organizer(self, session_id: uuid.UUID, organizer_id: uuid.UUID) -> Session:
        session = self.sessions.get(session_id)
        if session is None or session.organizer_id != organizer_id:
            raise SessionNotFound
        return session

    # -- escrita -----------------------------------------------------------

    def create(self, organizer_id: uuid.UUID, data: SessionCreate) -> Session:
        try:
            room = self.room_service.get_for_organizer(data.room_id, organizer_id)
        except RoomNotFound:
            raise

        self._require_future(data.starts_at)

        # O filme é buscado antes da trava de sala ocupada, e não depois: a
        # trava passou a comparar intervalos, e o intervalo depende da duração
        # do filme. Ver decisão D37.
        movie = get_catalog_provider().get(data.catalog_id)
        if movie is None:
            raise MovieNotFound

        ocupa_ate = occupation_end(data.starts_at, movie.runtime_minutes)
        if self.sessions.overlaps(room.id, data.starts_at, ocupa_ate):
            raise RoomBusy

        prices = self._build_prices(room, {p.sector_id: p.price_cents for p in data.prices})

        session = Session(
            organizer_id=organizer_id,
            room_id=room.id,
            # Cópia dos dados do filme no momento da criação. Ver decisão D13.
            catalog_id=movie.id,
            movie_title=movie.title,
            movie_overview=movie.overview,
            movie_poster_url=movie.poster_url,
            movie_backdrop_url=movie.backdrop_url,
            movie_runtime_minutes=movie.runtime_minutes,
            movie_year=movie.release_year,
            movie_age_rating=movie.age_rating,
            starts_at=data.starts_at,
            occupies_until=ocupa_ate,
            audio=data.audio,
            screen_format=data.screen_format,
            status=SessionStatus.PUBLISHED if data.publish else SessionStatus.DRAFT,
        )
        return self.sessions.create(session, prices)

    def create_batch(self, organizer_id: uuid.UUID, data: SessionRepeat) -> dict:
        """Cria a mesma sessão em vários dias, no mesmo horário.

        Dia ocupado é pulado e volta em `skipped` com o motivo, em vez de
        abortar o lote inteiro. Ver decisão D27.
        """
        created_sessions: list[Session] = []
        skipped: list[dict] = []

        for day in sorted(set(data.dates))[:MAX_BATCH_DATES]:
            starts_at = datetime.combine(day, data.time_of_day, tzinfo=LOCAL_TIMEZONE)

            try:
                created_sessions.append(
                    self.create(
                        organizer_id,
                        SessionCreate(
                            catalog_id=data.catalog_id,
                            room_id=data.room_id,
                            starts_at=starts_at,
                            audio=data.audio,
                            screen_format=data.screen_format,
                            prices=data.prices,
                            publish=data.publish,
                        ),
                    )
                )
            except RoomBusy:
                skipped.append(
                    {"date": day, "reason": "A sala já estava ocupada nesse intervalo"}
                )
            except SessionInThePast:
                skipped.append({"date": day, "reason": "Data e horário já passaram"})

        return {"created": created_sessions, "skipped": skipped}

    def has_any_ticket(self, session_id: uuid.UUID) -> bool:
        return (
            self.db.scalar(select(Ticket.id).where(Ticket.session_id == session_id).limit(1))
            is not None
        )

    def delete(self, session_id: uuid.UUID, organizer_id: uuid.UUID) -> None:
        """Apaga a sessão de vez — só rascunho, e só sem ingresso.

        Sessão publicada sai do cartaz com despublicar; sessão que já vendeu
        não some, porque quem comprou precisa continuar enxergando o que
        comprou. Para essas o caminho é cancelar. Ver decisão D28.
        """
        session = self.get_for_organizer(session_id, organizer_id)

        if self.has_any_ticket(session_id):
            raise SessionHasTickets
        if session.status is SessionStatus.PUBLISHED:
            raise SessionIsPublished

        self.db.delete(session)
        self.db.commit()

    def update(
        self, session_id: uuid.UUID, organizer_id: uuid.UUID, data: SessionUpdate
    ) -> Session:
        session = self.get_for_organizer(session_id, organizer_id)
        self._require_not_cancelled(session)

        if data.starts_at is not None and data.starts_at != session.starts_at:
            # Mudar a hora por baixo de quem já tem ingresso é pior que recusar
            # a edição: o sistema não tem como avisar essas pessoas.
            if self.has_any_ticket(session_id):
                raise SessionHasTickets
            self._require_future(data.starts_at)

            # A duração vem da cópia guardada na própria sessão, não de uma
            # nova consulta ao catálogo: o filme é o mesmo, e o que o ingresso
            # promete é o que foi gravado na venda. Ver decisões D13 e D37.
            ocupa_ate = occupation_end(data.starts_at, session.movie_runtime_minutes)
            if self.sessions.overlaps(
                session.room_id, data.starts_at, ocupa_ate, ignoring=session.id
            ):
                raise RoomBusy

            session.starts_at = data.starts_at
            session.occupies_until = ocupa_ate

        if data.audio is not None:
            session.audio = data.audio
        if data.screen_format is not None:
            session.screen_format = data.screen_format

        if data.prices is not None:
            novos = self._build_prices(
                session.room, {p.sector_id: p.price_cents for p in data.prices}
            )
            # Monta os novos antes de mexer nos atuais: se a validação falhar,
            # a sessão fica intacta em vez de perder os preços que tinha.
            #
            # O flush no meio é necessário porque o SQLAlchemy inseriria os
            # novos antes de apagar os antigos, e o índice único de
            # (sessão, setor) recusaria a operação.
            session.prices.clear()
            self.db.flush()
            session.prices = novos

        return self.sessions.save(session)

    def publish(self, session_id: uuid.UUID, organizer_id: uuid.UUID) -> Session:
        session = self.get_for_organizer(session_id, organizer_id)
        self._require_not_cancelled(session)
        self._require_future(session.starts_at)
        session.status = SessionStatus.PUBLISHED
        return self.sessions.save(session)

    def unpublish(self, session_id: uuid.UUID, organizer_id: uuid.UUID) -> Session:
        session = self.get_for_organizer(session_id, organizer_id)
        self._require_not_cancelled(session)
        session.status = SessionStatus.DRAFT
        return self.sessions.save(session)

    def occupied_seat_count(self, session_id: uuid.UUID) -> int:
        """Ingressos que ocupam poltrona — mesmo critério do índice que impede
        vender duas vezes, então desistência do cliente não conta."""
        return (
            self.db.scalar(
                select(func.count())
                .select_from(Ticket)
                .where(
                    Ticket.session_id == session_id,
                    Ticket.status.in_(OCCUPY_SEAT),
                )
            )
            or 0
        )

    def ticket_counts(
        self, session_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, tuple[int, int]]:
        """Por sessão: (quantos ocupam poltrona, quantos existem ao todo).

        A primeira contagem decide se dá para cancelar, a segunda se dá para
        apagar — sessão que um dia teve pedido não some. Uma consulta só, para
        o painel não virar N+1. Ver decisão D31.
        """
        if not session_ids:
            return {}

        linhas = self.db.execute(
            select(
                Ticket.session_id,
                func.count().filter(Ticket.status.in_(OCCUPY_SEAT)),
                func.count(),
            )
            .where(Ticket.session_id.in_(session_ids))
            .group_by(Ticket.session_id)
        ).all()
        return {sid: (ocupam, total) for sid, ocupam, total in linhas}

    def cancel(self, session_id: uuid.UUID, organizer_id: uuid.UUID) -> Session:
        """Cancela a sessão — só enquanto ela estiver vazia.

        Com ingresso vendido a operação é recusada: o sistema não avisa nem
        estorna ninguém, então o anúncio sozinho deixaria a pessoa com um QR
        morto. Para tirar do cartaz uma sessão que vai acontecer, o caminho é
        despublicar. Ver decisão D30.
        """
        session = self.get_for_organizer(session_id, organizer_id)
        self._require_not_cancelled(session)

        sold = self.occupied_seat_count(session_id)
        if sold:
            raise SessionSold(sold)

        session.status = SessionStatus.CANCELLED
        return self.sessions.save(session)

    def cancel_orders(self, session_id: uuid.UUID, organizer_id: uuid.UUID) -> int:
        """Cancela todos os pedidos da sessão. Devolve quantos.

        Passo separado do cancelamento da sessão de propósito: desfazer compras
        de pessoas reais precisa ser pedido, não vir embutido. Despublica antes
        de esvaziar, senão alguém compra no meio da operação. Ver decisão D30.
        """
        session = self.get_for_organizer(session_id, organizer_id)
        self._require_not_cancelled(session)

        if session.status is SessionStatus.PUBLISHED:
            session.status = SessionStatus.DRAFT
            self.sessions.save(session)

        return OrderService(self.db).cancel_for_session(session_id)

    # -- apoio -------------------------------------------------------------

    @staticmethod
    def _require_future(starts_at: datetime) -> None:
        if starts_at <= datetime.now(timezone.utc):
            raise SessionInThePast

    @staticmethod
    def _require_not_cancelled(session: Session) -> None:
        if session.status is SessionStatus.CANCELLED:
            raise SessionAlreadyCancelled

    @staticmethod
    def _build_prices(room, por_setor: dict[uuid.UUID, int]) -> list[SessionSectorPrice]:
        """Todo setor da sala precisa ter preço.

        Sem essa trava, uma sessão poderia ir ao ar com um setor sem valor, e o
        erro só apareceria na hora em que alguém tentasse comprar aquela
        poltrona.
        """
        missing = [s.name for s in room.sectors if s.id not in por_setor]
        if missing:
            raise PricesDoNotCoverSectors(missing)

        valid_ids = {s.id for s in room.sectors}
        return [
            # `room_id` explícito: é ele que a chave composta usa para provar
            # que o setor é desta sala. Ver decisão D35.
            SessionSectorPrice(sector_id=sid, room_id=room.id, price_cents=amount)
            for sid, amount in por_setor.items()
            if sid in valid_ids
        ]
