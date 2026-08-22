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
from app.models.session import Session, SessionSectorPrice, SessionStatus
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
            # Fileira A, junto ao acesso: dois espaços para cadeira de rodas,
            # cada um com a poltrona do acompanhante ao lado, mais dois assentos
            # largos. A fileira F fica no corredor, para mobilidade reduzida.
            "special_seats": [
                ("A1", SeatKind.WHEELCHAIR),
                ("A2", SeatKind.COMPANION),
                ("A3", SeatKind.WHEELCHAIR),
                ("A4", SeatKind.COMPANION),
                ("A11", SeatKind.OBESE),
                ("A12", SeatKind.OBESE),
                ("F1", SeatKind.REDUCED_MOBILITY),
                ("F12", SeatKind.REDUCED_MOBILITY),
            ],
        },
        {
            "name": "VIP",
            "rows": 2,
            "seats_per_row": 8,
            "display_order": 1,
            "special_seats": [
                ("A1", SeatKind.WHEELCHAIR),
                ("A2", SeatKind.COMPANION),
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

HORARIOS = [
    (1, 19, 0),
    (2, 21, 30),
    (3, 16, 0),
    (5, 20, 15),
]


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
                sectors=[
                    Sector(
                        name=s["name"],
                        rows=s["rows"],
                        seats_per_row=s["seats_per_row"],
                        display_order=s["display_order"],
                        special_seats=[
                            SeatAttribute(seat_code=codigo, kind=tipo)
                            for codigo, tipo in s["special_seats"]
                        ],
                    )
                    for s in SALA["sectors"]
                ],
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

        for filme, (dias, hora, minuto) in zip(filmes, HORARIOS):
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
                starts_at=quando,
                status=SessionStatus.PUBLISHED,
                prices=[
                    SessionSectorPrice(sector_id=setor.id, price_cents=PRECOS[setor.name])
                    for setor in sala.sectors
                ],
            )
            db.add(sessao)
            criados.append(f"sessão {filme.title} — {quando:%d/%m às %H:%M}")
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
