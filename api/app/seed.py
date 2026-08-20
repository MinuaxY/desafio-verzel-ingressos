"""Popula o banco com os usuários exigidos pelo desafio.

Idempotente: rodar de novo não duplica nem sobrescreve. Executar com
`python -m app.seed` com o ambiente virtual ativo.
"""
from app.core.security import hash_password
from app.db import SessionLocal
from app.models.user import Role, User

SENHA_PADRAO = "verzel123"

USUARIOS = [
    ("Organizador Demo", "organizador@verzel.dev", Role.ORGANIZER),
    ("Cliente Um", "cliente1@verzel.dev", Role.CUSTOMER),
    ("Cliente Dois", "cliente2@verzel.dev", Role.CUSTOMER),
    ("Portaria Demo", "portaria@verzel.dev", Role.GATE),
]


def run() -> None:
    db = SessionLocal()
    try:
        criados, existentes = [], []
        for nome, email, papel in USUARIOS:
            if db.query(User).filter(User.email == email).first():
                existentes.append(email)
                continue
            db.add(
                User(
                    name=nome,
                    email=email,
                    password_hash=hash_password(SENHA_PADRAO),
                    role=papel,
                )
            )
            criados.append(email)
        db.commit()

        print(f"Criados:   {len(criados)}")
        for e in criados:
            print(f"  + {e}")
        if existentes:
            print(f"Ja existiam: {len(existentes)}")
            for e in existentes:
                print(f"  = {e}")
        print(f"\nSenha de todos: {SENHA_PADRAO}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
