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

SENHA_MINIMA = 8


def _pede_senha() -> str:
    senha = getpass.getpass("Senha: ")
    if len(senha) < SENHA_MINIMA:
        raise SystemExit(f"A senha precisa de ao menos {SENHA_MINIMA} caracteres.")
    if senha != getpass.getpass("Repita a senha: "):
        raise SystemExit("As senhas não conferem.")
    return senha


def criar(nome: str, email: str, papel: Role, senha: str | None = None) -> None:
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).first():
            raise SystemExit(f"Já existe conta com o e-mail {email}.")

        db.add(
            User(
                name=nome,
                email=email,
                password_hash=hash_password(senha or _pede_senha()),
                role=papel,
            )
        )
        db.commit()
        print(f"Criado: {nome} <{email}> como {papel.value}")
    finally:
        db.close()


def promover(email: str, papel: Role) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            raise SystemExit(f"Não há conta com o e-mail {email}.")

        anterior = user.role
        user.role = papel
        db.commit()
        print(f"{email}: {anterior.value} → {papel.value}")
    finally:
        db.close()


def listar() -> None:
    db = SessionLocal()
    try:
        contas = db.query(User).order_by(User.role, User.email).all()
        if not contas:
            print("Nenhuma conta cadastrada.")
            return
        print(f"{'PAPEL':<12} {'E-MAIL':<34} NOME")
        for u in contas:
            print(f"{u.role.value:<12} {u.email:<34} {u.name}")
    finally:
        db.close()


def main(argv: list[str]) -> None:
    if not argv:
        print(__doc__)
        raise SystemExit(1)

    comando, *resto = argv

    if comando == "listar":
        listar()
    elif comando in ("criar-organizador", "criar-portaria"):
        if len(resto) != 2:
            raise SystemExit(f'Uso: python -m app.admin {comando} "Nome" email@dominio')
        papel = Role.ORGANIZER if comando == "criar-organizador" else Role.GATE
        criar(resto[0], resto[1], papel)
    elif comando == "promover":
        if len(resto) != 2:
            raise SystemExit("Uso: python -m app.admin promover email@dominio PAPEL")
        try:
            papel = Role(resto[1].upper())
        except ValueError:
            validos = ", ".join(p.value for p in Role)
            raise SystemExit(f"Papel inválido. Use um de: {validos}")
        promover(resto[0], papel)
    else:
        raise SystemExit(f"Comando desconhecido: {comando}\n{__doc__}")


if __name__ == "__main__":
    main(sys.argv[1:])
