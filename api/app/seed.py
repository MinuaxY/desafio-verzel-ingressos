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
)
from app.models.user import Role, User

SENHA_PADRAO = "verzel123"

USUARIOS = [
    ("Organizador Demo", "organizador@verzel.dev", Role.ORGANIZER),
    ("Cliente Um", "cliente1@verzel.dev", Role.CUSTOMER),
    ("Cliente Dois", "cliente2@verzel.dev", Role.CUSTOMER),
    ("Portaria Demo", "portaria@verzel.dev", Role.GATE),
]

# Fuso em que os horários da programação são interpretados. Ver decisão D27.
FUSO_LOCAL = ZoneInfo("America/Sao_Paulo")

# --------------------------------------------------------------------------
# Salas
#
# Tres geometrias diferentes de proposito: o mapa de assentos e a peca visual
# do projeto, e uma sala so mostraria sempre o mesmo desenho. A Sala 1 e a
# original, citada no roteiro do README, e nao muda.
# --------------------------------------------------------------------------

SALAS = [
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

DIAS_DE_PROGRAMACAO = 10

# (indice da sala, hora, minuto). As salas nao começam juntas: numa
# multiplex real os horarios sao escalonados para a bilheteria e a portaria nao
# receberem tres plateias no mesmo minuto.
GRADE = [
    (0, 14, 0),
    (0, 17, 0),
    (0, 20, 0),
    (0, 22, 30),
    (1, 15, 30),
    (1, 18, 30),
    (1, 21, 15),
    (2, 16, 0),
    (2, 19, 0),
    (2, 21, 45),
]

# Combinacoes de exibicao, percorridas em rodizio. Variadas de proposito: quem
# abrir a vitrine ve as quatro possibilidades, em vez de dez sessoes iguais.
EXIBICOES = [
    (AudioType.DUBBED, ScreenFormat.TWO_D),
    (AudioType.SUBTITLED, ScreenFormat.THREE_D),
    (AudioType.DUBBED, ScreenFormat.THREE_D),
    (AudioType.SUBTITLED, ScreenFormat.TWO_D),
]


def _monta_setores(spec: list[dict]) -> list[Sector]:
    """Constroi os setores com as letras corretas.

    As fileiras sao continuas na sala: com a Plateia ocupando A a F, o VIP
    comeca em G. O deslocamento e acumulado aqui em vez de escrito nos dados,
    para que mudar o tamanho de um setor nao exija reescrever os codigos do
    seguinte.
    """
    setores: list[Sector] = []
    offset = 0

    for s in spec:
        setores.append(
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

    return setores


def _programacao(agora: datetime) -> list[tuple[int, datetime, int]]:
    """A grade inteira: (índice da sala, quando, índice do filme).

    Devolve só o que ainda está no futuro — rodar o seed às 21h não deve criar
    a sessão das 14h de hoje, que já teria passado.

    O filme de cada faixa avança um pouco a cada dia, em vez de ser sorteado:
    o cartaz muda ao longo da semana como o de um cinema de verdade, e o mesmo
    filme reaparece em dias e salas diferentes, que é o que dá o que buscar e
    o que filtrar. Sendo determinístico, duas execuções produzem a mesma coisa.
    """
    total_filmes = len(FixtureProvider().items)
    hoje = agora.date()
    grade: list[tuple[int, datetime, int]] = []

    for dia in range(DIAS_DE_PROGRAMACAO):
        data = hoje + timedelta(days=dia)
        for faixa, (sala, hora, minuto) in enumerate(GRADE):
            quando = datetime.combine(data, time(hora, minuto), tzinfo=FUSO_LOCAL)
            if quando <= agora:
                continue
            grade.append((sala, quando, (dia * 3 + faixa) % total_filmes))

    return grade


def _completa_campos_faltantes(sessao: Session, filme) -> list[str]:
    """Preenche o que a sessão não tinha por ter nascido antes da coluna.

    Aconteceu com a classificação indicativa, adicionada depois que o ambiente
    publicado já tinha dados. Nunca sobrescreve o que já está preenchido.
    """
    remendos = []
    if sessao.movie_age_rating is None and filme.age_rating:
        sessao.movie_age_rating = filme.age_rating
        remendos.append("classificação")
    if sessao.movie_backdrop_url is None and filme.backdrop_url:
        sessao.movie_backdrop_url = filme.backdrop_url
        remendos.append("arte")
    return remendos


def run() -> None:
    db = SessionLocal()
    criados: list[str] = []
    existentes: list[str] = []

    try:
        # -- usuarios ------------------------------------------------------
        for nome, email, papel in USUARIOS:
            if db.query(User).filter(User.email == email).first():
                existentes.append(f"usuário {email}")
                continue
            db.add(
                User(
                    name=nome,
                    email=email,
                    password_hash=hash_password(SENHA_PADRAO),
                    role=papel,
                )
            )
            criados.append(f"usuário {email}")
        db.commit()

        organizador = db.query(User).filter(User.role == Role.ORGANIZER).first()
        if organizador is None:
            print("Nenhum organizador no banco; nada mais a semear.")
            return

        # -- salas ---------------------------------------------------------
        salas: list[Room] = []
        for spec in SALAS:
            sala = db.query(Room).filter(Room.name == spec["name"]).first()
            if sala is None:
                sala = Room(
                    organizer_id=organizador.id,
                    name=spec["name"],
                    location=spec["location"],
                    sectors=_monta_setores(spec["sectors"]),
                )
                db.add(sala)
                db.commit()
                db.refresh(sala)
                acessiveis = sum(len(s.special_seats) for s in sala.sectors)
                criados.append(
                    f"sala {sala.name} ({sala.capacity} lugares, {acessiveis} acessíveis)"
                )
            else:
                existentes.append(f"sala {sala.name}")
            salas.append(sala)

        # -- sessoes -------------------------------------------------------
        filmes = FixtureProvider().items
        agora = datetime.now(FUSO_LOCAL)

        # As sessões que já existem, indexadas pela chave que o banco usa para
        # impedir duas na mesma sala e horário. É o que torna o seed idempotente
        # sem comparar título nem adivinhar o que já foi criado.
        #
        # Cancelada fica de fora: ela não ocupa mais o horário, e o seed pode
        # reocupá-lo como qualquer criação faria. Ver decisão D31.
        ja_existem = {
            (s.room_id, s.starts_at): s
            for s in db.query(Session).filter(Session.status != SessionStatus.CANCELLED)
        }

        novas = 0
        remendadas = 0
        por_dia: dict[date, int] = {}

        for indice_sala, quando, indice_filme in _programacao(agora):
            sala = salas[indice_sala]
            filme = filmes[indice_filme]

            existente = ja_existem.get((sala.id, quando))
            if existente is not None:
                if _completa_campos_faltantes(existente, filme):
                    remendadas += 1
                continue

            audio, formato = EXIBICOES[(indice_filme + quando.hour) % len(EXIBICOES)]
            db.add(
                Session(
                    organizer_id=organizador.id,
                    room_id=sala.id,
                    catalog_id=filme.id,
                    movie_title=filme.title,
                    movie_overview=filme.overview,
                    movie_poster_url=filme.poster_url,
                    movie_backdrop_url=filme.backdrop_url,
                    movie_runtime_minutes=filme.runtime_minutes,
                    movie_year=filme.release_year,
                    movie_age_rating=filme.age_rating,
                    starts_at=quando,
                    audio=audio,
                    screen_format=formato,
                    status=SessionStatus.PUBLISHED,
                    prices=[
                        SessionSectorPrice(
                            sector_id=setor.id,
                            room_id=sala.id,
                            price_cents=SALAS[indice_sala]["precos"][setor.name],
                        )
                        for setor in sala.sectors
                    ],
                )
            )
            novas += 1
            por_dia[quando.date()] = por_dia.get(quando.date(), 0) + 1

        db.commit()

        if novas:
            dias = sorted(por_dia)
            criados.append(
                f"{novas} sessões em {len(dias)} dias "
                f"({dias[0]:%d/%m} a {dias[-1]:%d/%m}), "
                f"{len({f.id for f in filmes})} filmes, {len(salas)} salas"
            )
        if remendadas:
            criados.append(f"{remendadas} sessões existentes completadas")
        if not novas and not remendadas:
            existentes.append("programação (nenhum horário novo a criar)")

        # -- relatorio -----------------------------------------------------
        print(f"Criados ({len(criados)}):")
        for item in criados:
            print(f"  + {item}")
        if existentes:
            print(f"\nJa existiam ({len(existentes)}):")
            for item in existentes:
                print(f"  = {item}")
        print(f"\nSenha de todos os usuarios: {SENHA_PADRAO}")

    finally:
        db.close()


if __name__ == "__main__":
    run()
