"""Regra de negócio das sessões."""
import uuid
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.catalog.factory import get_catalog_provider
from app.models.order import OCUPAM_ASSENTO, Ticket
from app.models.session import Session, SessionSectorPrice, SessionStatus
from app.repositories.room_repository import RoomRepository
from app.repositories.session_repository import SessionRepository
from app.schemas.session import SessionCreate, SessionRepeat, SessionUpdate
from app.services.order_service import OrderService
from app.services.room_service import RoomNotFound, RoomService

# Fuso em que as datas escolhidas pelo organizador são interpretadas. "Dia 24
# às 19h" é hora local de quem vai ao cinema. Ver decisão D27.
FUSO_LOCAL = ZoneInfo("America/Sao_Paulo")

# Quanto tempo uma sessão continua aparecendo para a portaria depois de
# começar. Uma sessão de duas horas com público chegando atrasado ainda está
# recebendo gente; sumir da lista nesse momento é o pior instante possível.
HORAS_DE_TOLERANCIA_NA_PORTARIA = timedelta(hours=6)

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


class SessionSold(Exception):
    """A sessão já vendeu: cancelar exige resolver com quem comprou antes."""

    def __init__(self, vendidos: int) -> None:
        self.vendidos = vendidos
        super().__init__(f"{vendidos} ingresso(s) vendido(s)")


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

    def listar_para_portaria(self) -> list[Session]:
        """Sessões que a portaria pode estar conferindo agora.

        A vitrine só mostra o que ainda vai começar, e faz sentido para quem
        compra. Para quem está na porta, não: a sessão sumia da lista no
        instante em que começava — bem no meio da entrada, com gente chegando
        atrasada. Sem conseguir escolher a sessão, o operador perdia justamente
        a checagem de "este ingresso é de outra sessão".

        A janela vai de algumas horas atrás até o fim do dia seguinte: cobre a
        sessão em andamento e as próximas do turno, sem despejar a programação
        do mês num seletor. Ver decisão D33.
        """
        agora = datetime.now(timezone.utc)
        itens, _ = self.sessions.list_published(
            a_partir_de=agora - HORAS_DE_TOLERANCIA_NA_PORTARIA,
            page=1,
            por_pagina=100,
        )
        return [s for s in itens if s.starts_at <= agora + timedelta(days=2)]

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

    def ingressos_vendidos(self, session_id: uuid.UUID) -> int:
        """Quantos ingressos desta sessão ocupam poltrona.

        Ingresso cancelado pelo próprio cliente não conta: a poltrona voltou
        para o estoque, e uma sessão em que todo mundo desistiu está vazia de
        novo. Mesmo critério do índice que impede vender duas vezes.
        """
        return (
            self.db.scalar(
                select(func.count())
                .select_from(Ticket)
                .where(
                    Ticket.session_id == session_id,
                    Ticket.status.in_(OCUPAM_ASSENTO),
                )
            )
            or 0
        )

    def contagens_de_ingressos(
        self, session_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, tuple[int, int]]:
        """Por sessão: (quantos ocupam poltrona, quantos existem ao todo).

        As duas contagens respondem perguntas diferentes do painel. A primeira
        diz se a sessão pode ser cancelada — cancelado não ocupa. A segunda diz
        se ela pode ser **apagada**: uma sessão que um dia teve pedido não some,
        mesmo que todos tenham sido cancelados depois, porque alguém pode
        precisar rastrear o que aconteceu com aquela compra.

        Uma consulta só para a lista inteira: uma por sessão transformaria o
        painel em N+1 conforme a programação cresce.
        """
        if not session_ids:
            return {}

        linhas = self.db.execute(
            select(
                Ticket.session_id,
                func.count().filter(Ticket.status.in_(OCUPAM_ASSENTO)),
                func.count(),
            )
            .where(Ticket.session_id.in_(session_ids))
            .group_by(Ticket.session_id)
        ).all()
        return {sid: (ocupam, total) for sid, ocupam, total in linhas}

    def cancelar(self, session_id: uuid.UUID, organizer_id: uuid.UUID) -> Session:
        """Cancela a sessão — só enquanto ela estiver vazia.

        Cancelar diz que a sessão **não vai acontecer**. Se alguém já comprou,
        esse anúncio sozinho não resolve nada: a pessoa continuaria com um QR
        na mão, e o sistema não tem como avisá-la nem como devolver o dinheiro.
        Então a operação é recusada, e o organizador tem que lidar com quem
        comprou antes — cancelando os pedidos — para só depois cancelar a
        sessão.

        Para tirar do cartaz uma sessão que **vai acontecer**, o caminho é
        despublicar: para de vender e quem já tem ingresso entra normalmente.
        Ver decisão D30.
        """
        sessao = self.obter_do_organizador(session_id, organizer_id)
        self._exige_nao_cancelada(sessao)

        vendidos = self.ingressos_vendidos(session_id)
        if vendidos:
            raise SessionSold(vendidos)

        sessao.status = SessionStatus.CANCELLED
        return self.sessions.save(sessao)

    def cancelar_pedidos(self, session_id: uuid.UUID, organizer_id: uuid.UUID) -> int:
        """Cancela de uma vez todos os pedidos da sessão. Devolve quantos.

        É o passo que falta para conseguir cancelar uma sessão que já vendeu.
        Fica separado do cancelamento da sessão de propósito: são duas
        decisões diferentes — desfazer as compras de pessoas reais é a que
        pesa, e embutir isso num botão chamado "cancelar sessão" faria o
        organizador tomá-la sem perceber.

        **Despublica antes**, e só então cancela. Não dá para esvaziar uma
        sessão que continua vendendo: alguém compraria no meio da operação e o
        organizador voltaria à mesma tela com um pedido novo. O despublicar é
        commitado primeiro, o que fecha a porta de entrada — resta a janela de
        um pedido que já estava em voo, e para esse a contagem devolvida
        denuncia a diferença.
        """
        sessao = self.obter_do_organizador(session_id, organizer_id)
        self._exige_nao_cancelada(sessao)

        if sessao.status is SessionStatus.PUBLISHED:
            sessao.status = SessionStatus.DRAFT
            self.sessions.save(sessao)

        return OrderService(self.db).cancelar_da_sessao(session_id)

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
