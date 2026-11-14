"""create table outbox_events

Outbox de eventos de domínio: gravada na mesma transação do caso de uso e lida pelo extrator
analítico (analytics/ingestion/extract_outbox.py) usando `sequence_id` como marca d'água.

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
        "outbox_events",
        sa.Column("event_id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("aggregate_type", sa.Text(), nullable=False),
        sa.Column("aggregate_id", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("sequence_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.PrimaryKeyConstraint("event_id", name=op.f("pk_outbox_events")),
    )
    op.create_index("ix_outbox_events_sequence_id", "outbox_events", ["sequence_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_outbox_events_sequence_id", table_name="outbox_events")
    op.drop_table("outbox_events")
