"""sessao cancelada libera o horario da sala

Revision ID: b7e412af9c03
Revises: a1c30d5e7b42
Create Date: 2026-08-22 22:20:00.000000

A constraint (room_id, starts_at) contava a sessao cancelada, e como cancelar
nao tem volta o horario ficava preso para sempre. Vira indice parcial, igual
ao das poltronas: cancelado nao ocupa.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7e412af9c03"
down_revision: Union[str, None] = "a1c30d5e7b42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # O nome e reaproveitado de proposito: e a mesma regra, so que agora
    # enxergando o estado da sessao.
    op.drop_constraint("uq_sessao_sala_horario", "sessions", type_="unique")
    op.create_index(
        "uq_sessao_sala_horario",
        "sessions",
        ["room_id", "starts_at"],
        unique=True,
        postgresql_where=sa.text("status <> 'CANCELLED'"),
    )


def downgrade() -> None:
    # Voltar exige que nao haja duas sessoes no mesmo horario com uma delas
    # cancelada -- caso que a versao nova permite e a antiga nao.
    op.drop_index("uq_sessao_sala_horario", table_name="sessions")
    op.create_unique_constraint(
        "uq_sessao_sala_horario", "sessions", ["room_id", "starts_at"]
    )
