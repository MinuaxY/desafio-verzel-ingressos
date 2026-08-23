"""Regra de negócio das salas."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.models.room import MAX_FILEIRAS, Room
from app.models.session import Session, SessionStatus
from app.repositories.room_repository import RoomRepository
from app.schemas.room import RoomIn, RoomUpdate


class RoomNameAlreadyUsed(Exception):
    pass


class RoomNotFound(Exception):
    pass


class RoomNotOwned(Exception):
    pass


class RoomTooTall(Exception):
    """A sala tem mais fileiras do que o alfabeto comporta."""

    def __init__(self, total: int) -> None:
        self.total = total
        super().__init__(str(total))


class RoomInUse(Exception):
    """A sala tem sessão futura: não sai do ar enquanto houver o que exibir."""

    def __init__(self, sessoes: int) -> None:
        self.sessoes = sessoes
        super().__init__(str(sessoes))


class RoomLayoutLocked(Exception):
    """A sala já foi usada: a geometria não muda mais.

    Mexer em fileiras, poltronas ou corredores depois de haver sessão faria a
    poltrona F12 de alguém deixar de existir. Nome e endereço continuam
    editáveis. Ver decisão D29.
    """


class SeatOutsideSector(Exception):
    """Marcaram como acessível uma poltrona que não existe na geometria."""

    def __init__(self, setor: str, codigos: list[str]) -> None:
        self.setor = setor
        self.codigos = codigos
        super().__init__(f"{setor}: {', '.join(codigos)}")


class RoomService:
    def __init__(self, db: DbSession) -> None:
        self.db = db
        self.rooms = RoomRepository(db)

    def listar(self, organizer_id: uuid.UUID) -> list[Room]:
        return self.rooms.list_by_organizer(organizer_id)

    def criar(self, organizer_id: uuid.UUID, dados: RoomIn) -> Room:
        if self.rooms.get_by_name(organizer_id, dados.name):
            raise RoomNameAlreadyUsed

        self._valida_altura(dados)
        self._valida_assentos_especiais(dados)

        return self.rooms.create(
            organizer_id=organizer_id,
            name=dados.name,
            location=dados.location,
            sectors=[s.model_dump() for s in dados.sectors],
        )

    def obter_do_organizador(self, room_id: uuid.UUID, organizer_id: uuid.UUID) -> Room:
        """Sala inexistente e sala de outro organizador são erros distintos.

        Quem não é dono recebe 'não encontrada', e não 'não é sua': confirmar a
        existência entregaria a quem sonda quais salas existem no sistema.
        """
        room = self.rooms.get(room_id)
        if room is None or room.organizer_id != organizer_id:
            raise RoomNotFound
        return room

    @staticmethod
    def _valida_altura(dados: RoomIn) -> None:
        """As fileiras da sala são contínuas e nomeadas por letra, então a soma
        de todos os setores precisa caber no alfabeto. Sem esta trava, o setor
        seguinte à fileira Z receberia caracteres que não são letras."""
        total = sum(s.rows for s in dados.sectors)
        if total > MAX_FILEIRAS:
            raise RoomTooTall(total)

    @staticmethod
    def _valida_assentos_especiais(dados: RoomIn) -> None:
        """Poltrona acessível precisa existir na geometria do setor.

        Sem essa trava, marcar a Z9 num setor que vai só até a fileira H seria
        aceito, e a poltrona acessível simplesmente não apareceria no mapa —
        um lugar que o sistema acha que existe e a sala não tem.

        O deslocamento das fileiras é reproduzido a partir da própria lista de
        entrada: os setores ainda não existem no banco, então não dá para
        perguntar ao model qual é o offset de cada um.
        """
        offset = 0
        for setor in sorted(dados.sectors, key=lambda s: (s.display_order, s.name)):
            if setor.special_seats:
                letras = {chr(ord("A") + offset + i) for i in range(setor.rows)}
                fora = [
                    s.seat_code
                    for s in setor.special_seats
                    if s.seat_code[0] not in letras
                    or not (1 <= int(s.seat_code[1:] or 0) <= setor.seats_per_row)
                ]
                if fora:
                    raise SeatOutsideSector(setor.name, fora)
            offset += setor.rows

    # -- edição --------------------------------------------------------------

    def sessoes_da_sala(self, room_id: uuid.UUID) -> tuple[int, int]:
        """Quantas sessões a sala tem no total, e quantas ainda vão acontecer."""
        total = (
            self.db.scalar(
                select(func.count()).select_from(Session).where(Session.room_id == room_id)
            )
            or 0
        )
        futuras = (
            self.db.scalar(
                select(func.count())
                .select_from(Session)
                .where(
                    Session.room_id == room_id,
                    Session.starts_at > datetime.now(timezone.utc),
                    Session.status != SessionStatus.CANCELLED,
                )
            )
            or 0
        )
        return total, futuras

    def atualizar(self, room_id: uuid.UUID, organizer_id: uuid.UUID, dados: RoomUpdate) -> Room:
        """Nome e endereço, sempre. Geometria, só enquanto a sala for nova.

        Trocar o layout depois de existir sessão faria a poltrona vendida
        apontar para um lugar que não existe mais. Ver decisão D29.
        """
        sala = self.obter_do_organizador(room_id, organizer_id)

        if dados.name is not None and dados.name != sala.name:
            existente = self.rooms.get_by_name(organizer_id, dados.name)
            if existente is not None and existente.id != sala.id:
                raise RoomNameAlreadyUsed
            sala.name = dados.name

        if dados.location is not None:
            sala.location = dados.location or None

        if dados.sectors is not None:
            total, _ = self.sessoes_da_sala(room_id)
            if total > 0:
                raise RoomLayoutLocked

            molde = RoomIn(name=sala.name, location=sala.location, sectors=dados.sectors)
            self._valida_altura(molde)
            self._valida_assentos_especiais(molde)
            self.rooms.replace_sectors(sala, [s.model_dump() for s in dados.sectors])

        return self.rooms.save(sala)

    # -- remoção -------------------------------------------------------------

    def remover(self, room_id: uuid.UUID, organizer_id: uuid.UUID) -> Room | None:
        """Apaga a sala se ela nunca serviu; desativa se já serviu.

        Sala com sessão futura não sai de jeito nenhum — há gente podendo
        comprar para ela agora.

        A distinção entre apagar e desativar existe porque sessão passada
        aponta para a sala, e o histórico de quem comprou precisa continuar
        fazendo sentido. Sala que nunca teve sessão não tem histórico a
        preservar, e deixá-la desativada só acumularia lixo na lista.
        Ver decisão D28.

        Devolve a sala desativada, ou None quando ela foi apagada.
        """
        sala = self.obter_do_organizador(room_id, organizer_id)
        total, futuras = self.sessoes_da_sala(room_id)

        if futuras > 0:
            raise RoomInUse(futuras)

        if total == 0:
            self.rooms.delete(sala)
            return None

        return self.rooms.deactivate(sala)
