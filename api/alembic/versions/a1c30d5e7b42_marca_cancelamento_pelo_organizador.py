"""marca cancelamento pelo organizador

Revision ID: a1c30d5e7b42
Revises: 8fab6c7372a6
Create Date: 2026-08-22 21:40:00.000000

O pedido passa a registrar se quem cancelou foi o organizador. Sem essa
distincao, o cliente que teve a sessao cancelada leria apenas "cancelado" e
concluiria que a desistencia foi dele.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1c30d5e7b42"
down_revision: Union[str, None] = "8fab6c7372a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # A coluna e NOT NULL numa tabela que ja pode ter linhas: entra com
    # server_default para as existentes e perde o default em seguida, para que
    # o valor passe a vir sempre da aplicacao.
    op.add_column(
        "orders",
        sa.Column(
            "cancelled_by_organizer",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column("orders", "cancelled_by_organizer", server_default=None)


def downgrade() -> None:
    op.drop_column("orders", "cancelled_by_organizer")
