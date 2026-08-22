"""Regra de negócio das salas."""
import uuid

from sqlalchemy.orm import Session as DbSession

from app.models.room import MAX_FILEIRAS, Room
from app.repositories.room_repository import RoomRepository
from app.schemas.room import RoomIn


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


class SeatOutsideSector(Exception):
    """Marcaram como acessível uma poltrona que não existe na geometria."""

    def __init__(self, setor: str, codigos: list[str]) -> None:
        self.setor = setor
        self.codigos = codigos
        super().__init__(f"{setor}: {', '.join(codigos)}")


class RoomService:
    def __init__(self, db: DbSession) -> None:
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

    def desativar(self, room_id: uuid.UUID, organizer_id: uuid.UUID) -> Room:
        # Desativa em vez de apagar: sessões passadas apontam para a sala, e o
        # histórico de quem comprou precisa continuar fazendo sentido.
        return self.rooms.deactivate(self.obter_do_organizador(room_id, organizer_id))
