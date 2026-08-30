"""Popula o banco com os dados exigidos pelo desafio.

Cria os quatro usuários, três salas de geometrias diferentes e uma programação
de dez dias, para que o sistema possa ser percorrido sem montar nada do zero e
para que a vitrine tenha volume de verdade — um cartaz com quatro sessões não
exercita paginação, filtro por dia nem busca, que é justamente o que precisa
ser visto funcionando.

Idempotente: rodar de novo no mesmo dia não duplica nem sobrescreve. Executar
com `python -m app.seed`.

Os filmes vêm do provedor local, não do TMDb: o seed precisa funcionar sem rede
e sem chave, e produzir sempre o mesmo resultado. Ver decisão D8.
"""
import sys
import uuid
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

# O console do Windows usa cp1252 por padrão e embaralharia os acentos dos
# títulos. Quem roda o seed é quem está avaliando o projeto; a saída precisa
# estar legível.
if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") != "utf8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.catalog.fixture import FixtureProvider  # noqa: E402
from app.core.security import hash_password
from app.db import SessionLocal
from app.models.room import Room, SeatAttribute, SeatKind, Sector
from app.models.session import (
    AudioType,
    ScreenFormat,
    Session,
    SessionSectorPrice,
    SessionStatus,
    occupation_end,
)
from app.models.user import Role, User

DEFAULT_PASSWORD = "verzel123"

USERS = [
    ("Organizador Demo", "organizador@verzel.dev", Role.ORGANIZER),
    ("Cliente Um", "cliente1@verzel.dev", Role.CUSTOMER),
    ("Cliente Dois", "cliente2@verzel.dev", Role.CUSTOMER),
    ("Portaria Demo", "portaria@verzel.dev", Role.GATE),
]

# Fuso em que os horários da programação são interpretados. Ver decisão D27.
LOCAL_TIMEZONE = ZoneInfo("America/Sao_Paulo")

# --------------------------------------------------------------------------
# Salas
#
# Tres geometrias diferentes de proposito: o mapa de assentos e a peca visual
# do projeto, e uma sala so mostraria sempre o mesmo desenho. A Sala 1 e a
# original, citada no roteiro do README, e nao muda.
# --------------------------------------------------------------------------

ROOMS = [
    {
        "name": "Sala 1 — Cine Verzel",
        "location": "Av. Paulista, 1000 — São Paulo",
        "precos": {"Plateia": 3200, "VIP": 5400},
        "sectors": [
            # display_order cresce da tela para o fundo da sala.
            {
                "name": "Plateia",
                "rows": 6,
                "seats_per_row": 12,
                "display_order": 0,
                # Dois corredores, deixando blocos de 3, 6 e 3 — o desenho de
                # sala media, com passagem lateral dos dois lados.
                "aisles": [3, 9],
                # Posicao relativa ao setor: (fileira, poltrona, tipo). A letra
                # e calculada a partir do deslocamento da sala, e nao escrita a
                # mao — fixar "A1" quebrou quando as fileiras passaram a ser
                # continuas e o VIP virou G e H.
                #
                # Primeira fileira, junto ao acesso: dois espacos para cadeira
                # de rodas, cada um com a poltrona do acompanhante ao lado,
                # mais dois assentos largos. A ultima fileira fica no corredor,
                # para mobilidade reduzida.
                "special_seats": [
                    (0, 1, SeatKind.WHEELCHAIR),
                    (0, 2, SeatKind.COMPANION),
                    (0, 3, SeatKind.WHEELCHAIR),
                    (0, 4, SeatKind.COMPANION),
                    (0, 11, SeatKind.OBESE),
                    (0, 12, SeatKind.OBESE),
                    (5, 1, SeatKind.REDUCED_MOBILITY),
                    (5, 12, SeatKind.REDUCED_MOBILITY),
                ],
            },
            {
                "name": "VIP",
                "rows": 2,
                "seats_per_row": 8,
                "display_order": 1,
                # Sem corredor: bloco unico, centralizado sobre o miolo da
                # plateia. Dividir oito lugares em 4+4 criaria uma passagem que
                # nao coincide com nenhuma das duas da plateia, e tres
                # corredores desalinhados fazem o olho ler bagunca mesmo com os
                # centros iguais. Um bloco solido no centro le como area VIP.
                "aisles": [],
                "special_seats": [
                    (0, 1, SeatKind.WHEELCHAIR),
                    (0, 2, SeatKind.COMPANION),
                ],
            },
        ],
    },
    {
        "name": "Sala 2 — Cine Verzel",
        "location": "Av. Paulista, 1000 — São Paulo",
        "precos": {"Plateia": 2600},
        # Sala pequena, de setor unico e um corredor central: e o caso em que
        # o mapa nao tem VIP nenhum, que tambem precisa ficar bonito.
        "sectors": [
            {
                "name": "Plateia",
                "rows": 4,
                "seats_per_row": 8,
                "display_order": 0,
                "aisles": [4],
                "special_seats": [
                    (0, 1, SeatKind.WHEELCHAIR),
                    (0, 2, SeatKind.COMPANION),
                    (3, 8, SeatKind.REDUCED_MOBILITY),
                ],
            },
        ],
    },
    {
        "name": "Sala 3 — Cine Verzel (IMAX)",
        "location": "Av. Paulista, 1000 — São Paulo",
        "precos": {"Plateia": 3800, "VIP": 6200},
        # A maior: quatro blocos de poltronas e VIP no fundo, para mostrar o
        # mapa no limite do que a tela precisa acomodar.
        "sectors": [
            {
                "name": "Plateia",
                "rows": 8,
                "seats_per_row": 14,
                "display_order": 0,
                "aisles": [3, 7, 11],
                "special_seats": [
                    (0, 1, SeatKind.WHEELCHAIR),
                    (0, 2, SeatKind.COMPANION),
                    (0, 3, SeatKind.WHEELCHAIR),
                    (0, 4, SeatKind.COMPANION),
                    (0, 13, SeatKind.OBESE),
                    (0, 14, SeatKind.OBESE),
                    (7, 1, SeatKind.REDUCED_MOBILITY),
                    (7, 14, SeatKind.REDUCED_MOBILITY),
                ],
            },
            {
                "name": "VIP",
                "rows": 2,
                "seats_per_row": 10,
                "display_order": 1,
                "aisles": [],
                "special_seats": [
                    (0, 1, SeatKind.WHEELCHAIR),
                    (0, 2, SeatKind.COMPANION),
                ],
            },
        ],
    },
]

# --------------------------------------------------------------------------
# Programacao
#
# Horarios de exibicao de verdade, no fuso de Sao Paulo. Somar horas sobre
# "agora" produziria sessao as tres da manha, o que nenhum cinema faz -- e e o
# primeiro dado que quem avalia ve.
# --------------------------------------------------------------------------

SCHEDULE_DAYS = 10

# Horario da primeira sessao de cada sala. As salas nao abrem juntas: numa
# multiplex real os horarios sao escalonados para a bilheteria e a portaria nao
# receberem tres plateias no mesmo minuto.
FIRST_SHOWTIME = [time(14, 0), time(15, 30), time(16, 0)]

# Depois da ultima sessao que comeca antes disso, a sala fecha.
LAST_SHOWTIME = time(22, 30)

# As sessoes seguintes nao saem de uma grade fixa: sao empilhadas a partir da
# duracao real de cada filme mais a folga de limpeza, e arredondadas para cima
# no proximo quarto de hora.
#
# A grade fixa anterior tinha intervalos de 150 a 180 minutos, e o filme mais
# longo do catalogo ocupa 192 -- o proprio seed produzia sobreposicao, e a
# trava da D37 passou a recusa-la. Empilhar pela duracao real resolve na
# origem, e e como um cinema monta a programacao de verdade.
ROUND_TO_MINUTES = 15

# Combinacoes de exibicao, percorridas em rodizio. Variadas de proposito: quem
# abrir a vitrine ve as quatro possibilidades, em vez de dez sessoes iguais.
EXIBICOES = [
    (AudioType.DUBBED, ScreenFormat.TWO_D),
    (AudioType.SUBTITLED, ScreenFormat.THREE_D),
    (AudioType.DUBBED, ScreenFormat.THREE_D),
    (AudioType.SUBTITLED, ScreenFormat.TWO_D),
]


def _build_sectors(spec: list[dict]) -> list[Sector]:
    """Constroi os setores com as letras corretas.

    As fileiras sao continuas na sala: com a Plateia ocupando A a F, o VIP
    comeca em G. O deslocamento e acumulado aqui em vez de escrito nos dados,
    para que mudar o tamanho de um setor nao exija reescrever os codigos do
    seguinte.
    """
    sectors: list[Sector] = []
    offset = 0

    for s in spec:
        sectors.append(
            Sector(
                name=s["name"],
                rows=s["rows"],
                seats_per_row=s["seats_per_row"],
                display_order=s["display_order"],
                aisles=s.get("aisles", []),
                special_seats=[
                    SeatAttribute(
                        seat_code=f"{chr(ord('A') + offset + fileira)}{numero}", kind=tipo
                    )
                    for fileira, numero, tipo in s["special_seats"]
                ],
            )
        )
        offset += s["rows"]

    return sectors


def _schedule(now: datetime) -> list[tuple[int, datetime, int]]:
    """A grade inteira: (índice da sala, quando, índice do filme).

    Cada sala é preenchida empilhando sessões a partir da duração real do filme
    escolhido, e não de horários fixos: a sala só volta a receber público
    quando a sessão anterior libera. É assim que a programação nunca produz a
    sobreposição que a D37 recusa.

    Devolve só o que ainda está no futuro — rodar o seed às 21h não deve criar
    a sessão das 14h de hoje, que já teria passado.

    O filme de cada faixa avança um pouco a cada dia, em vez de ser sorteado: o
    cartaz muda ao longo da semana como o de um cinema de verdade, e o mesmo
    filme reaparece em dias e salas diferentes, que é o que dá o que buscar e o
    que filtrar. Sendo determinístico, duas execuções produzem a mesma coisa.
    """
    movies = FixtureProvider().items
    hoje = now.date()
    grade: list[tuple[int, datetime, int]] = []
    proximo_filme = 0

    for day in range(SCHEDULE_DAYS):
        data = hoje + timedelta(days=day)

        for room, abertura in enumerate(FIRST_SHOWTIME):
            starts_at = datetime.combine(data, abertura, tzinfo=LOCAL_TIMEZONE)
            fecha = datetime.combine(data, LAST_SHOWTIME, tzinfo=LOCAL_TIMEZONE)

            while starts_at <= fecha:
                indice = proximo_filme % len(movies)
                proximo_filme += 1

                if starts_at > now:
                    grade.append((room, starts_at, indice))

                starts_at = _next_slot(starts_at, movies[indice].runtime_minutes)

    return grade


def _next_slot(comeca: datetime, duracao: int | None) -> datetime:
    """Quando a sala pode receber a próxima plateia, em hora redonda.

    Arredondar para cima é o que faz a programação parecer de cinema: ninguém
    anuncia sessão às 19h07. Para cima, e nunca para baixo, senão a sessão
    seguinte começaria antes de a sala estar livre.
    """
    free_at = occupation_end(comeca, duracao)
    sobra = free_at.minute % ROUND_TO_MINUTES
    if sobra:
        free_at += timedelta(minutes=ROUND_TO_MINUTES - sobra)
    return free_at.replace(second=0, microsecond=0)


def _fill_missing_fields(session: Session, movie) -> list[str]:
    """Preenche o que a sessão não tinha por ter nascido antes da coluna.

    Aconteceu com a classificação indicativa, adicionada depois que o ambiente
    publicado já tinha dados. Nunca sobrescreve o que já está preenchido.
    """
    patched = []
    if session.movie_age_rating is None and movie.age_rating:
        session.movie_age_rating = movie.age_rating
        patched.append("classificação")
    if session.movie_backdrop_url is None and movie.backdrop_url:
        session.movie_backdrop_url = movie.backdrop_url
        patched.append("arte")
    return patched


def run() -> None:
    db = SessionLocal()
    created: list[str] = []
    already_there: list[str] = []

    try:
        # -- usuarios ------------------------------------------------------
        for name, email, role in USERS:
            if db.query(User).filter(User.email == email).first():
                already_there.append(f"usuário {email}")
                continue
            db.add(
                User(
                    name=name,
                    email=email,
                    password_hash=hash_password(DEFAULT_PASSWORD),
                    role=role,
                )
            )
            created.append(f"usuário {email}")
        db.commit()

        organizer = db.query(User).filter(User.role == Role.ORGANIZER).first()
        if organizer is None:
            print("Nenhum organizador no banco; nada mais a semear.")
            return

        # -- salas ---------------------------------------------------------
        rooms: list[Room] = []
        for spec in ROOMS:
            room = db.query(Room).filter(Room.name == spec["name"]).first()
            if room is None:
                room = Room(
                    organizer_id=organizer.id,
                    name=spec["name"],
                    location=spec["location"],
                    sectors=_build_sectors(spec["sectors"]),
                )
                db.add(room)
                db.commit()
                db.refresh(room)
                acessiveis = sum(len(s.special_seats) for s in room.sectors)
                created.append(
                    f"sala {room.name} ({room.capacity} lugares, {acessiveis} acessíveis)"
                )
            else:
                already_there.append(f"sala {room.name}")
            rooms.append(room)

        # -- sessoes -------------------------------------------------------
        movies = FixtureProvider().items
        now = datetime.now(LOCAL_TIMEZONE)

        # As sessões que já existem, indexadas pela chave que o banco usa para
        # impedir duas na mesma sala e horário. É o que torna o seed idempotente
        # sem comparar título nem adivinhar o que já foi criado.
        #
        # Cancelada fica de fora: ela não ocupa mais o horário, e o seed pode
        # reocupá-lo como qualquer criação faria. Ver decisão D31.
        vivas = list(db.query(Session).filter(Session.status != SessionStatus.CANCELLED))
        ja_existem = {(s.room_id, s.starts_at): s for s in vivas}

        # Os intervalos que cada sala já tem ocupados. O seed grava direto no
        # banco, sem passar pelo serviço, então precisa respeitar a trava de
        # sobreposição por conta própria — senão a primeira colisão derruba a
        # execução inteira com uma violação de constraint. Ver decisão D37.
        occupied_ranges: dict[uuid.UUID, list[tuple[datetime, datetime]]] = {}
        for s in vivas:
            occupied_ranges.setdefault(s.room_id, []).append((s.starts_at, s.occupies_until))

        skipped_count = 0
        new_count = 0
        remendadas = 0
        por_dia: dict[date, int] = {}

        for indice_sala, starts_at, indice_filme in _schedule(now):
            room = rooms[indice_sala]
            movie = movies[indice_filme]

            existente = ja_existem.get((room.id, starts_at))
            if existente is not None:
                if _fill_missing_fields(existente, movie):
                    remendadas += 1
                continue

            free_at = occupation_end(starts_at, movie.runtime_minutes)
            if any(
                starts_at < fim and free_at > inicio
                for inicio, fim in occupied_ranges.get(room.id, ())
            ):
                # Horário já ocupado por uma sessão de execução anterior, com
                # outra duração. Pular é o certo: o seed completa a programação,
                # não a reescreve.
                skipped_count += 1
                continue

            audio, formato = EXIBICOES[(indice_filme + starts_at.hour) % len(EXIBICOES)]
            db.add(
                Session(
                    organizer_id=organizer.id,
                    room_id=room.id,
                    catalog_id=movie.id,
                    movie_title=movie.title,
                    movie_overview=movie.overview,
                    movie_poster_url=movie.poster_url,
                    movie_backdrop_url=movie.backdrop_url,
                    movie_runtime_minutes=movie.runtime_minutes,
                    movie_year=movie.release_year,
                    movie_age_rating=movie.age_rating,
                    starts_at=starts_at,
                    occupies_until=occupation_end(starts_at, movie.runtime_minutes),
                    audio=audio,
                    screen_format=formato,
                    status=SessionStatus.PUBLISHED,
                    prices=[
                        SessionSectorPrice(
                            sector_id=sector.id,
                            room_id=room.id,
                            price_cents=ROOMS[indice_sala]["precos"][sector.name],
                        )
                        for sector in room.sectors
                    ],
                )
            )
            occupied_ranges.setdefault(room.id, []).append((starts_at, free_at))
            new_count += 1
            por_dia[starts_at.date()] = por_dia.get(starts_at.date(), 0) + 1

        db.commit()

        if new_count:
            days = sorted(por_dia)
            created.append(
                f"{new_count} sessões em {len(days)} dias "
                f"({days[0]:%d/%m} a {days[-1]:%d/%m}), "
                f"{len({f.id for f in movies})} filmes, {len(rooms)} salas"
            )
        if remendadas:
            created.append(f"{remendadas} sessões existentes completadas")
        if skipped_count:
            already_there.append(f"{skipped_count} horários já ocupados por sessões anteriores")
        if not new_count and not remendadas:
            already_there.append("programação (nenhum horário novo a criar)")

        # -- relatorio -----------------------------------------------------
        print(f"Criados ({len(created)}):")
        for item in created:
            print(f"  + {item}")
        if already_there:
            print(f"\nJa existiam ({len(already_there)}):")
            for item in already_there:
                print(f"  = {item}")
        print(f"\nSenha de todos os usuarios: {DEFAULT_PASSWORD}")

    finally:
        db.close()


if __name__ == "__main__":
    run()
