"""Criação de contas privilegiadas, fora da API.

O cadastro público cria sempre cliente. Organizador e portaria não saem dele:
quem opera a plataforma é quem concede esses papéis, e um endpoint público que
aceitasse o papel como parâmetro seria escalada de privilégio — foi exatamente
o defeito que este módulo existe para fechar. Ver decisão D34.

Ficar na linha de comando, e não numa rota protegida, é decisão consciente para
o tamanho deste projeto: não existe papel de administrador no modelo, e criar um
só para hospedar essa operação traria mais superfície do que resolve. Quem tem
acesso ao servidor já pode tudo; quem não tem, não passa por aqui.

    python -m app.admin criar-organizador "Cine Verzel" contato@cine.dev
    python -m app.admin criar-portaria "Portaria Sala 1" portaria@cine.dev
    python -m app.admin listar
    python -m app.admin promover contato@cine.dev ORGANIZER

A senha é pedida no terminal, sem eco. Passá-la como argumento a deixaria no
histórico do shell e na lista de processos.
"""
import getpass
import sys

from app.core.security import hash_password
from app.db import SessionLocal
from app.models.user import Role, User

# O console do Windows usa cp1252 por padrão e embaralharia os acentos.
if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") != "utf8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MIN_PASSWORD_LENGTH = 8


def _ask_password() -> str:
    password = getpass.getpass("Senha: ")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise SystemExit(f"A senha precisa de ao menos {MIN_PASSWORD_LENGTH} caracteres.")
    if password != getpass.getpass("Repita a senha: "):
        raise SystemExit("As senhas não conferem.")
    return password


def create(name: str, email: str, role: Role, password: str | None = None) -> None:
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).first():
            raise SystemExit(f"Já existe conta com o e-mail {email}.")

        db.add(
            User(
                name=name,
                email=email,
                password_hash=hash_password(password or _ask_password()),
                role=role,
            )
        )
        db.commit()
        print(f"Criado: {name} <{email}> como {role.value}")
    finally:
        db.close()


def promote(email: str, role: Role) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            raise SystemExit(f"Não há conta com o e-mail {email}.")

        previous = user.role
        user.role = role
        db.commit()
        print(f"{email}: {previous.value} → {role.value}")
    finally:
        db.close()


def list_all() -> None:
    db = SessionLocal()
    try:
        accounts = db.query(User).order_by(User.role, User.email).all()
        if not accounts:
            print("Nenhuma conta cadastrada.")
            return
        print(f"{'PAPEL':<12} {'E-MAIL':<34} NOME")
        for u in accounts:
            print(f"{u.role.value:<12} {u.email:<34} {u.name}")
    finally:
        db.close()


def main(argv: list[str]) -> None:
    if not argv:
        print(__doc__)
        raise SystemExit(1)

    command, *rest = argv

    if command == "listar":
        list_all()
    elif command in ("criar-organizador", "criar-portaria"):
        if len(rest) != 2:
            raise SystemExit(f'Uso: python -m app.admin {command} "Nome" email@dominio')
        role = Role.ORGANIZER if command == "criar-organizador" else Role.GATE
        create(rest[0], rest[1], role)
    elif command == "promover":
        if len(rest) != 2:
            raise SystemExit("Uso: python -m app.admin promover email@dominio PAPEL")
        try:
            role = Role(rest[1].upper())
        except ValueError:
            valid_ids = ", ".join(p.value for p in Role)
            raise SystemExit(f"Papel inválido. Use um de: {valid_ids}")
        promote(rest[0], role)
    else:
        raise SystemExit(f"Comando desconhecido: {command}\n{__doc__}")


if __name__ == "__main__":
    main(sys.argv[1:])
