"""cria a tabela outbox_eventos

Outbox de eventos de domínio: gravada na mesma transação do caso de uso e lida pelo extrator
analítico (analytics/ingestao/extrair_outbox.py) usando `id_sequencial` como marca d'água.

Revision ID: 0001
Revises:
Create Date: 2026-11-02 16:15:15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "outbox_eventos",
        sa.Column("id_evento", sa.UUID(), nullable=False),
        sa.Column("tipo_evento", sa.Text(), nullable=False),
        sa.Column("versao_schema", sa.Integer(), nullable=False),
        sa.Column("tipo_agregado", sa.Text(), nullable=False),
        sa.Column("id_agregado", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ocorrido_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "registrado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id_sequencial", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.PrimaryKeyConstraint("id_evento", name=op.f("pk_outbox_eventos")),
    )
    op.create_index(
        "ix_outbox_eventos_id_sequencial", "outbox_eventos", ["id_sequencial"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_outbox_eventos_id_sequencial", table_name="outbox_eventos")
    op.drop_table("outbox_eventos")
