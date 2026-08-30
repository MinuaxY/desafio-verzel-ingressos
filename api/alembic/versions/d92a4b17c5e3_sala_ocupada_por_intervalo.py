"""sala ocupada por intervalo, nao por igualdade de horario

Revision ID: d92a4b17c5e3
Revises: c4d81f6a2e70
Create Date: 2026-08-28 20:40:00.000000

A trava de agenda comparava apenas igualdade de starts_at, entao duas sessoes
de duas horas na mesma sala, as 20:00 e as 20:01, nao colidiam: a sala ficava
com duas plateias.

Passa a usar uma constraint de exclusao sobre o intervalo que a sessao ocupa
-- inicio + duracao do filme + folga de limpeza. Cancelada continua de fora,
pela mesma razao da D31.

Os dados existentes podem ter sobreposicoes criadas sob a regra antiga. Elas
sao resolvidas cancelando uma das sessoes do par, preferindo sempre manter a
que ja vendeu ingresso. Ver decisao D37.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d92a4b17c5e3"
down_revision: Union[str, None] = "c4d81f6a2e70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Mesmos valores de app/models/session.py. Repetidos aqui de proposito: uma
# migration descreve o banco no momento em que rodou, e nao pode mudar de
# resultado porque uma constante da aplicacao mudou depois.
DEFAULT_RUNTIME_MINUTES = 120
TURNAROUND_MINUTES = 20


def upgrade() -> None:
    # btree_gist permite combinar igualdade (room_id) com sobreposicao de
    # intervalo na mesma constraint. Sem ela, o gist nao sabe indexar uuid.
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    # -- a coluna que materializa a ocupacao -------------------------------
    # Materializada porque a constraint e um indice, e indice do Postgres so
    # aceita expressao imutavel. `timestamptz + interval` e apenas estavel.
    op.add_column("sessions", sa.Column("occupies_until", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        f"""
        UPDATE sessions
           SET occupies_until = starts_at + make_interval(
                 mins => COALESCE(movie_runtime_minutes, {DEFAULT_RUNTIME_MINUTES})
                         + {TURNAROUND_MINUTES})
        """
    )
    op.alter_column("sessions", "occupies_until", nullable=False)

    # -- resolve as sobreposicoes que a regra antiga deixou passar ---------
    #
    # Cancelar, e nao apagar: cancelada nao ocupa a sala (D31), entao a
    # constraint a aceita, e o historico de quem olhou aquela sessao continua
    # existindo. Apagar reescreveria o passado.
    #
    # A escolha de qual cancelar nao e arbitraria: entre as duas, sai a que tem
    # menos ingresso ocupando poltrona. Cancelar uma sessao vendida quebraria a
    # promessa feita a quem comprou, que e justamente o que a D30 protege. No
    # empate, sai a que comeca depois.
    #
    # Um por vez, em laco: cancelar uma sessao pode resolver varios pares de
    # uma vez, e recalcular a cada passo evita cancelar mais do que o preciso.
    op.execute(
        """
        DO $$
        DECLARE
            perdedora uuid;
        BEGIN
            LOOP
                SELECT CASE
                         WHEN a.vendidos < b.vendidos THEN a.id
                         WHEN b.vendidos < a.vendidos THEN b.id
                         WHEN a.starts_at >= b.starts_at THEN a.id
                         ELSE b.id
                       END
                  INTO perdedora
                  FROM (
                        SELECT s.*, (
                                 SELECT count(*) FROM tickets t
                                  WHERE t.session_id = s.id AND t.status <> 'CANCELLED'
                               ) AS vendidos
                          FROM sessions s WHERE s.status <> 'CANCELLED'
                       ) a
                  JOIN (
                        SELECT s.*, (
                                 SELECT count(*) FROM tickets t
                                  WHERE t.session_id = s.id AND t.status <> 'CANCELLED'
                               ) AS vendidos
                          FROM sessions s WHERE s.status <> 'CANCELLED'
                       ) b
                    ON a.room_id = b.room_id
                   AND a.id < b.id
                   AND tstzrange(a.starts_at, a.occupies_until)
                    && tstzrange(b.starts_at, b.occupies_until)
                 LIMIT 1;

                EXIT WHEN perdedora IS NULL;

                UPDATE sessions SET status = 'CANCELLED' WHERE id = perdedora;
                -- Os ingressos da sessao cancelada acompanham, como faz o
                -- cancelamento normal (D30). Utilizado nao e tocado: e o
                -- registro de quem entrou.
                UPDATE tickets SET status = 'CANCELLED'
                 WHERE session_id = perdedora AND status IN ('RESERVED', 'VALID');
                perdedora := NULL;
            END LOOP;
        END $$;
        """
    )

    # -- as travas ---------------------------------------------------------
    op.create_check_constraint(
        "ck_session_occupation", "sessions", "occupies_until > starts_at"
    )
    op.execute(
        """
        ALTER TABLE sessions ADD CONSTRAINT ex_session_room_overlap
        EXCLUDE USING gist (
            room_id WITH =,
            tstzrange(starts_at, occupies_until) WITH &&
        ) WHERE (status <> 'CANCELLED')
        """
    )

    # O indice antigo vira ruido: comecar no mesmo instante e um caso
    # particular de sobrepor, e a exclusao ja cobre. Duas travas dizendo
    # a mesma coisa e exatamente o tipo de duplicidade que confunde quem le.
    op.drop_index("uq_sessao_sala_horario", table_name="sessions")


def downgrade() -> None:
    op.create_index(
        "uq_sessao_sala_horario",
        "sessions",
        ["room_id", "starts_at"],
        unique=True,
        postgresql_where=sa.text("status <> 'CANCELLED'"),
    )
    # O Alembic nao conhece o tipo "exclude" em drop_constraint, entao vai
    # em SQL puro.
    op.execute("ALTER TABLE sessions DROP CONSTRAINT ex_session_room_overlap")
    op.drop_constraint("ck_session_occupation", "sessions", type_="check")
    op.drop_column("sessions", "occupies_until")
    # A extensao fica: outra coisa pode ter passado a depender dela, e remover
    # extensao em downgrade e mais arriscado que deixar.
