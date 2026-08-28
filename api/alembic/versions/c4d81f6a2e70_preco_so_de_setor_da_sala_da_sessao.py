"""preco so de setor da sala da sessao

Revision ID: c4d81f6a2e70
Revises: b7e412af9c03
Create Date: 2026-08-25 21:10:00.000000

session_sector_prices apontava para sessions.id e sectors.id de forma
independente, entao nada no banco impedia gravar o preco de um setor de outra
sala. So o servico conferia.

Passa a usar duas chaves estrangeiras compostas que compartilham room_id: a
primeira exige que a sessao esteja nessa sala, a segunda exige o mesmo do
setor. Sendo a mesma coluna, as duas falam da mesma sala.

O minimo do preco tambem sobe de 0 para 1 centavo, alinhando o banco ao
contrato da API. Ver decisoes D33 e D35.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4d81f6a2e70"
down_revision: Union[str, None] = "b7e412af9c03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- alvos das chaves compostas ---------------------------------------
    # O Postgres so aceita chave estrangeira apontando para colunas com
    # unicidade declarada. (id, room_id) e trivialmente unico por causa da
    # chave primaria, mas precisa estar dito.
    op.create_unique_constraint("uq_session_id_room", "sessions", ["id", "room_id"])
    op.create_unique_constraint("uq_sector_id_room", "sectors", ["id", "room_id"])

    # -- a coluna que prova a regra ---------------------------------------
    # Entra permitindo nulo para as linhas que ja existem serem preenchidas a
    # partir da propria sessao; so depois vira obrigatoria.
    op.add_column("session_sector_prices", sa.Column("room_id", sa.Uuid(), nullable=True))
    op.execute(
        """
        UPDATE session_sector_prices AS p
           SET room_id = s.room_id
          FROM sessions AS s
         WHERE s.id = p.session_id
        """
    )

    # Preco orfao nao deveria existir, mas se existir a coluna ficaria nula e a
    # migration quebraria no NOT NULL com uma mensagem que nao explica nada.
    # Apagar e o certo: preco sem sessao nao e dado, e lixo.
    op.execute("DELETE FROM session_sector_prices WHERE room_id IS NULL")
    op.alter_column("session_sector_prices", "room_id", nullable=False)

    # Preco zerado tambem some: o pagamento simulado recusa valor zero, entao
    # essas linhas so produziriam pedidos que ninguem consegue pagar.
    op.execute("UPDATE session_sector_prices SET price_cents = 1 WHERE price_cents < 1")

    # -- troca as chaves simples pelas compostas --------------------------
    op.drop_constraint(
        "session_sector_prices_session_id_fkey", "session_sector_prices", type_="foreignkey"
    )
    op.drop_constraint(
        "session_sector_prices_sector_id_fkey", "session_sector_prices", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_session_price_session_room",
        "session_sector_prices",
        "sessions",
        ["session_id", "room_id"],
        ["id", "room_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_session_price_sector_room",
        "session_sector_prices",
        "sectors",
        ["sector_id", "room_id"],
        ["id", "room_id"],
        ondelete="CASCADE",
    )

    # -- nomes em ingles, e o minimo de um centavo ------------------------
    op.drop_constraint("uq_preco_sessao_setor", "session_sector_prices", type_="unique")
    op.create_unique_constraint(
        "uq_session_price_sector", "session_sector_prices", ["session_id", "sector_id"]
    )
    op.drop_constraint("ck_preco_nao_negativo", "session_sector_prices", type_="check")
    op.create_check_constraint(
        "ck_session_price_positive", "session_sector_prices", "price_cents >= 1"
    )


def downgrade() -> None:
    op.drop_constraint("ck_session_price_positive", "session_sector_prices", type_="check")
    op.create_check_constraint(
        "ck_preco_nao_negativo", "session_sector_prices", "price_cents >= 0"
    )
    op.drop_constraint("uq_session_price_sector", "session_sector_prices", type_="unique")
    op.create_unique_constraint(
        "uq_preco_sessao_setor", "session_sector_prices", ["session_id", "sector_id"]
    )

    op.drop_constraint(
        "fk_session_price_sector_room", "session_sector_prices", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_session_price_session_room", "session_sector_prices", type_="foreignkey"
    )
    op.create_foreign_key(
        "session_sector_prices_session_id_fkey",
        "session_sector_prices",
        "sessions",
        ["session_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "session_sector_prices_sector_id_fkey",
        "session_sector_prices",
        "sectors",
        ["sector_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_column("session_sector_prices", "room_id")
    op.drop_constraint("uq_sector_id_room", "sectors", type_="unique")
    op.drop_constraint("uq_session_id_room", "sessions", type_="unique")
