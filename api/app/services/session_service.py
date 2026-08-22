"""Regra de negócio das sessões."""
import uuid
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.catalog.factory import get_catalog_provider
from app.models.order import Ticket
from app.models.session import Session, SessionSectorPrice, SessionStatus
from app.repositories.room_repository import RoomRepository
from app.repositories.session_repository import SessionRepository
from app.schemas.session import SessionCreate, SessionRepeat, SessionUpdate
from app.services.room_service import RoomNotFound, RoomService

# Fuso em que as datas escolhidas pelo organizador são interpretadas. "Dia 24
# às 19h" é hora local de quem vai ao cinema. Ver decisão D27.
FUSO_LOCAL = ZoneInfo("America/Sao_Paulo")

# Teto para a criação em lote. Uma programação de cinema não passa de algumas
# semanas, e sem limite um engano criaria centenas de sessões.
MAX_DATAS_POR_LOTE = 60


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


class SessionHasTickets(Exception):
    """A sessão já vendeu ingresso: não pode ser apagada nem ter o horário
    mudado por baixo de quem comprou."""


class SessionIsPublished(Exception):
    """Sessão publicada sai do cartaz com despublicar, não com exclusão."""


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
        dia: date | None = None,
        incluir_passadas: bool = False,
        page: int = 1,
        por_pagina: int = 12,
    ) -> tuple[list[Session], int]:
        # Sessão que já começou não interessa a quem quer comprar.
        corte = None if incluir_passadas else datetime.now(timezone.utc)
        return self.sessions.list_published(
            busca=busca, a_partir_de=corte, dia=dia, page=page, por_pagina=por_pagina
        )

    def dias_em_cartaz(self, *, dias: int = 14, busca: str | None = None) -> dict[date, int]:
        """Quantas sessões há em cada dia daqui para a frente.

        A barra de datas precisa saber quais dias têm o que mostrar: oferecer
        um dia vazio como se fosse opção é convidar o clique que não leva a
        lugar nenhum.
        """
        agora = datetime.now(timezone.utc)
        fim = datetime.combine(
            agora.astimezone(FUSO_LOCAL).date() + timedelta(days=dias),
            time.min,
            tzinfo=FUSO_LOCAL,
        )
        return self.sessions.dias_com_sessao(a_partir_de=agora, ate=fim, busca=busca)

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

    def criar_em_lote(self, organizer_id: uuid.UUID, dados: SessionRepeat) -> dict:
        """Cria a mesma sessão em vários dias, no mesmo horário.

        Dia em que a sala já está ocupada é **pulado**, e não aborta o lote:
        obrigar a refazer a seleção inteira por causa de um dia ocupado joga
        fora o trabalho de escolher os outros nove. O que ficou de fora volta
        na resposta, com o motivo, para o organizador resolver esses casos.
        Ver decisão D27.
        """
        criadas: list[Session] = []
        puladas: list[dict] = []

        for dia in sorted(set(dados.dates))[:MAX_DATAS_POR_LOTE]:
            quando = datetime.combine(dia, dados.time_of_day, tzinfo=FUSO_LOCAL)

            try:
                criadas.append(
                    self.criar(
                        organizer_id,
                        SessionCreate(
                            catalog_id=dados.catalog_id,
                            room_id=dados.room_id,
                            starts_at=quando,
                            audio=dados.audio,
                            screen_format=dados.screen_format,
                            prices=dados.prices,
                            publish=dados.publish,
                        ),
                    )
                )
            except RoomBusy:
                puladas.append({"date": dia, "reason": "Já havia sessão nessa sala nesse horário"})
            except SessionInThePast:
                puladas.append({"date": dia, "reason": "Data e horário já passaram"})

        return {"created": criadas, "skipped": puladas}

    def tem_ingressos(self, session_id: uuid.UUID) -> bool:
        return (
            self.db.scalar(select(Ticket.id).where(Ticket.session_id == session_id).limit(1))
            is not None
        )

    def excluir(self, session_id: uuid.UUID, organizer_id: uuid.UUID) -> None:
        """Apaga a sessão de vez — só rascunho, e só sem ingresso.

        Sessão publicada sai do cartaz com despublicar; sessão que já vendeu
        não some, porque quem comprou precisa continuar enxergando o que
        comprou. Para essas o caminho é cancelar. Ver decisão D28.
        """
        sessao = self.obter_do_organizador(session_id, organizer_id)

        if self.tem_ingressos(session_id):
            raise SessionHasTickets
        if sessao.status is SessionStatus.PUBLISHED:
            raise SessionIsPublished

        self.db.delete(sessao)
        self.db.commit()

    def atualizar(
        self, session_id: uuid.UUID, organizer_id: uuid.UUID, dados: SessionUpdate
    ) -> Session:
        sessao = self.obter_do_organizador(session_id, organizer_id)
        self._exige_nao_cancelada(sessao)

        if dados.starts_at is not None and dados.starts_at != sessao.starts_at:
            # Mudar a hora por baixo de quem já tem ingresso é pior que recusar
            # a edição: o sistema não tem como avisar essas pessoas.
            if self.tem_ingressos(session_id):
                raise SessionHasTickets
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
