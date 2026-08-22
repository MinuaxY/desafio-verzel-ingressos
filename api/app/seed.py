"""Popula o banco com os dados exigidos pelo desafio.

Cria os quatro usuários, uma sala com dois setores e sessões publicadas com
ingressos disponíveis, para que o sistema possa ser percorrido sem montar nada
do zero.

Idempotente: rodar de novo não duplica nem sobrescreve. Executar com
`python -m app.seed`.

Os filmes vêm do provedor local, não do TMDb: o seed precisa funcionar sem
rede e sem chave, e produzir sempre o mesmo resultado. Ver decisão D8.
"""
import sys
from datetime import datetime, timedelta
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

SALA = {
    "name": "Sala 1 — Cine Verzel",
    "location": "Av. Paulista, 1000 — São Paulo",
    "sectors": [
        # display_order cresce da tela para o fundo da sala.
        {
            "name": "Plateia",
            "rows": 6,
            "seats_per_row": 12,
            "display_order": 0,
            # Dois corredores, deixando blocos de 3, 6 e 3 — o desenho de sala
            # media, com passagem lateral dos dois lados.
            "aisles": [3, 9],
            # Posicao relativa ao setor: (fileira, poltrona, tipo). A letra e
            # calculada a partir do deslocamento da sala, e nao escrita a mao —
            # fixar "A1" quebrou quando as fileiras passaram a ser continuas e
            # o VIP virou G e H.
            #
            # Primeira fileira, junto ao acesso: dois espacos para cadeira de
            # rodas, cada um com a poltrona do acompanhante ao lado, mais dois
            # assentos largos. A ultima fileira fica no corredor, para
            # mobilidade reduzida.
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
            # nao coincide com nenhuma das duas da plateia, e tres corredores
            # desalinhados fazem o olho ler bagunca mesmo com os centros
            # iguais. Um bloco solido no centro le como area VIP.
            "aisles": [],
            "special_seats": [
                (0, 1, SeatKind.WHEELCHAIR),
                (0, 2, SeatKind.COMPANION),
            ],
        },
    ],
}

PRECOS = {"Plateia": 3200, "VIP": 5400}  # em centavos

# Sessões em dias à frente, para que o seed nunca nasça com sessão no passado:
# sessão passada não aparece na vitrine e quem for avaliar veria a tela vazia.
#
# Os horários são de exibição de verdade, no fuso de São Paulo. Somar horas
# sobre "agora" produziria sessão às três da manhã, o que nenhum cinema faz —
# e é o primeiro dado que quem avalia vê.
FUSO_LOCAL = ZoneInfo("America/Sao_Paulo")

# Dia, hora, minuto, áudio e formato. Variados de propósito: quem abrir a
# vitrine vê as quatro combinações possíveis, em vez de quatro sessões iguais.
HORARIOS = [
    (1, 19, 0, AudioType.DUBBED, ScreenFormat.TWO_D),
    (2, 21, 30, AudioType.SUBTITLED, ScreenFormat.THREE_D),
    (3, 16, 0, AudioType.DUBBED, ScreenFormat.THREE_D),
    (5, 20, 15, AudioType.SUBTITLED, ScreenFormat.TWO_D),
]


def _monta_setores() -> list[Sector]:
    """Constroi os setores com as letras corretas.

    As fileiras sao continuas na sala: com a Plateia ocupando A a F, o VIP
    comeca em G. O deslocamento e acumulado aqui em vez de escrito nos dados,
    para que mudar o tamanho de um setor nao exija reescrever os codigos do
    seguinte.
    """
    setores: list[Sector] = []
    offset = 0

    for s in SALA["sectors"]:
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


def _proximo(dias: int, hora: int, minuto: int) -> datetime:
    local = datetime.now(FUSO_LOCAL) + timedelta(days=dias)
    return local.replace(hour=hora, minute=minuto, second=0, microsecond=0)


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

        # -- sala ----------------------------------------------------------
        sala = db.query(Room).filter(Room.name == SALA["name"]).first()
        if sala is None:
            sala = Room(
                organizer_id=organizador.id,
                name=SALA["name"],
                location=SALA["location"],
                sectors=_monta_setores(),
            )
            db.add(sala)
            db.commit()
            db.refresh(sala)
            acessiveis = sum(len(s.special_seats) for s in sala.sectors)
            criados.append(
                f"sala {sala.name} ({sala.capacity} lugares, "
                f"{acessiveis} acessíveis)"
            )
        else:
            existentes.append(f"sala {sala.name}")

        # -- sessoes -------------------------------------------------------
        filmes = FixtureProvider().items[: len(HORARIOS)]

        for filme, (dias, hora, minuto, audio, formato) in zip(filmes, HORARIOS):
            quando = _proximo(dias, hora, minuto)

            # A comparação é por filme, não por horário. Os horários são
            # relativos a agora, então rodar o seed noutro dia produziria
            # horários diferentes, nada bateria e as sessões seriam duplicadas
            # — foi o que aconteceu antes desta correção.
            ja_existe = (
                db.query(Session)
                .filter(
                    Session.room_id == sala.id,
                    Session.catalog_id == filme.id,
                    Session.starts_at > datetime.now(FUSO_LOCAL),
                )
                .first()
            )
            if ja_existe:
                # A sessão já existe, mas pode ter nascido antes de alguma
                # coluna existir — foi o que aconteceu com a classificação
                # indicativa, adicionada depois que o ambiente publicado já
                # tinha dados. Completar aqui evita que a demonstração fique
                # com campo vazio, e não sobrescreve nada que já esteja
                # preenchido.
                remendos = []
                if ja_existe.movie_age_rating is None and filme.age_rating:
                    ja_existe.movie_age_rating = filme.age_rating
                    remendos.append("classificação")
                if ja_existe.movie_backdrop_url is None and filme.backdrop_url:
                    ja_existe.movie_backdrop_url = filme.backdrop_url
                    remendos.append("arte")

                # Áudio e formato não têm estado "vazio": a migration deu a
                # todas as sessões antigas o padrão do banco. Só ajusta quando
                # a sessão ainda está exatamente nesse padrão e o seed previa
                # outra coisa — assim uma escolha deliberada do organizador
                # nunca é sobrescrita.
                no_padrao = (
                    ja_existe.audio is AudioType.SUBTITLED
                    and ja_existe.screen_format is ScreenFormat.TWO_D
                )
                if no_padrao and (audio, formato) != (AudioType.SUBTITLED, ScreenFormat.TWO_D):
                    ja_existe.audio = audio
                    ja_existe.screen_format = formato
                    remendos.append("exibição")

                if remendos:
                    db.commit()
                    criados.append(f"sessão {filme.title} — completada ({', '.join(remendos)})")
                else:
                    existentes.append(f"sessão {filme.title}")
                continue

            sessao = Session(
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
                    SessionSectorPrice(sector_id=setor.id, price_cents=PRECOS[setor.name])
                    for setor in sala.sectors
                ],
            )
            db.add(sessao)
            rotulo = "Dublado" if audio is AudioType.DUBBED else "Legendado"
            dimensao = "3D" if formato is ScreenFormat.THREE_D else "2D"
            criados.append(
                f"sessão {filme.title} — {quando:%d/%m às %H:%M} "
                f"({rotulo} {dimensao}, {filme.age_rating or 'sem classificação'})"
            )
        db.commit()

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
