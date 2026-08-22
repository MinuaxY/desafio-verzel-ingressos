"""Regra de negócio das sessões."""
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session as DbSession

from app.catalog.factory import get_catalog_provider
from app.models.session import Session, SessionSectorPrice, SessionStatus
from app.repositories.room_repository import RoomRepository
from app.repositories.session_repository import SessionRepository
from app.schemas.session import SessionCreate, SessionUpdate
from app.services.room_service import RoomNotFound, RoomService


class MovieNotFound(Exception):
    pass


class SessionNotFound(Exception):
    pass


class RoomBusy(Exception):
    """Já existe sessão nessa sala nesse horário."""


class SessionInThePast(Exception):
    pass


class PricesDoNotCoverSectors(Exception):
    def __init__(self, faltando: list[str]) -> None:
        self.faltando = faltando
        super().__init__(f"Sem preço para: {', '.join(faltando)}")


class SessionAlreadyCancelled(Exception):
    pass


class SessionService:
    def __init__(self, db: DbSession) -> None:
        self.db = db
        self.sessions = SessionRepository(db)
        self.rooms = RoomRepository(db)
        self.room_service = RoomService(db)

    # -- leitura pública ---------------------------------------------------

    def listar_publicas(
        self,
        *,
        busca: str | None = None,
        incluir_passadas: bool = False,
        page: int = 1,
        por_pagina: int = 12,
    ) -> tuple[list[Session], int]:
        # Sessão que já começou não interessa a quem quer comprar.
        corte = None if incluir_passadas else datetime.now(timezone.utc)
        return self.sessions.list_published(
            busca=busca, a_partir_de=corte, page=page, por_pagina=por_pagina
        )

    def obter_publica(self, session_id: uuid.UUID) -> Session:
        sessao = self.sessions.get(session_id)
        if sessao is None or not sessao.is_public:
            raise SessionNotFound
        return sessao

    # -- leitura do organizador -------------------------------------------

    def listar_do_organizador(self, organizer_id: uuid.UUID) -> list[Session]:
        return self.sessions.list_by_organizer(organizer_id)

    def obter_do_organizador(self, session_id: uuid.UUID, organizer_id: uuid.UUID) -> Session:
        sessao = self.sessions.get(session_id)
        if sessao is None or sessao.organizer_id != organizer_id:
            raise SessionNotFound
        return sessao

    # -- escrita -----------------------------------------------------------

    def criar(self, organizer_id: uuid.UUID, dados: SessionCreate) -> Session:
        try:
            sala = self.room_service.obter_do_organizador(dados.room_id, organizer_id)
        except RoomNotFound:
            raise

        self._exige_futuro(dados.starts_at)

        if self.sessions.exists_at(sala.id, dados.starts_at):
            raise RoomBusy

        filme = get_catalog_provider().get(dados.catalog_id)
        if filme is None:
            raise MovieNotFound

        precos = self._monta_precos(sala, {p.sector_id: p.price_cents for p in dados.prices})

        sessao = Session(
            organizer_id=organizer_id,
            room_id=sala.id,
            # Cópia dos dados do filme no momento da criação. Ver decisão D13.
            catalog_id=filme.id,
            movie_title=filme.title,
            movie_overview=filme.overview,
            movie_poster_url=filme.poster_url,
            movie_backdrop_url=filme.backdrop_url,
            movie_runtime_minutes=filme.runtime_minutes,
            movie_year=filme.release_year,
            movie_age_rating=filme.age_rating,
            starts_at=dados.starts_at,
            audio=dados.audio,
            screen_format=dados.screen_format,
            status=SessionStatus.PUBLISHED if dados.publish else SessionStatus.DRAFT,
        )
        return self.sessions.create(sessao, precos)

    def atualizar(
        self, session_id: uuid.UUID, organizer_id: uuid.UUID, dados: SessionUpdate
    ) -> Session:
        sessao = self.obter_do_organizador(session_id, organizer_id)
        self._exige_nao_cancelada(sessao)

        if dados.starts_at is not None and dados.starts_at != sessao.starts_at:
            self._exige_futuro(dados.starts_at)
            if self.sessions.exists_at(sessao.room_id, dados.starts_at):
                raise RoomBusy
            sessao.starts_at = dados.starts_at

        if dados.audio is not None:
            sessao.audio = dados.audio
        if dados.screen_format is not None:
            sessao.screen_format = dados.screen_format

        if dados.prices is not None:
            novos = self._monta_precos(
                sessao.room, {p.sector_id: p.price_cents for p in dados.prices}
            )
            # Monta os novos antes de mexer nos atuais: se a validação falhar,
            # a sessão fica intacta em vez de perder os preços que tinha.
            #
            # O flush no meio é necessário porque o SQLAlchemy inseriria os
            # novos antes de apagar os antigos, e o índice único de
            # (sessão, setor) recusaria a operação.
            sessao.prices.clear()
            self.db.flush()
            sessao.prices = novos

        return self.sessions.save(sessao)

    def publicar(self, session_id: uuid.UUID, organizer_id: uuid.UUID) -> Session:
        sessao = self.obter_do_organizador(session_id, organizer_id)
        self._exige_nao_cancelada(sessao)
        self._exige_futuro(sessao.starts_at)
        sessao.status = SessionStatus.PUBLISHED
        return self.sessions.save(sessao)

    def despublicar(self, session_id: uuid.UUID, organizer_id: uuid.UUID) -> Session:
        sessao = self.obter_do_organizador(session_id, organizer_id)
        self._exige_nao_cancelada(sessao)
        sessao.status = SessionStatus.DRAFT
        return self.sessions.save(sessao)

    def cancelar(self, session_id: uuid.UUID, organizer_id: uuid.UUID) -> Session:
        sessao = self.obter_do_organizador(session_id, organizer_id)
        self._exige_nao_cancelada(sessao)
        sessao.status = SessionStatus.CANCELLED
        return self.sessions.save(sessao)

    # -- apoio -------------------------------------------------------------

    @staticmethod
    def _exige_futuro(quando: datetime) -> None:
        if quando <= datetime.now(timezone.utc):
            raise SessionInThePast

    @staticmethod
    def _exige_nao_cancelada(sessao: Session) -> None:
        if sessao.status is SessionStatus.CANCELLED:
            raise SessionAlreadyCancelled

    @staticmethod
    def _monta_precos(sala, por_setor: dict[uuid.UUID, int]) -> list[SessionSectorPrice]:
        """Todo setor da sala precisa ter preço.

        Sem essa trava, uma sessão poderia ir ao ar com um setor sem valor, e o
        erro só apareceria na hora em que alguém tentasse comprar aquela
        poltrona.
        """
        faltando = [s.name for s in sala.sectors if s.id not in por_setor]
        if faltando:
            raise PricesDoNotCoverSectors(faltando)

        validos = {s.id for s in sala.sectors}
        return [
            SessionSectorPrice(sector_id=sid, price_cents=valor)
            for sid, valor in por_setor.items()
            if sid in validos
        ]
