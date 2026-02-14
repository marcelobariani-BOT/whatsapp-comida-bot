from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "8f427aec596e"  # <-- reemplazar por el id real
down_revision = "41fb75590f24"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversation_state",
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            sa.String(length=64),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stage", sa.String(length=32), nullable=False, server_default=sa.text("'NEW'")),
        sa.Column(
            "state",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_index("ix_conversation_state_tenant", "conversation_state", ["tenant_id"], unique=False)
    op.create_index("ix_conversation_state_stage", "conversation_state", ["stage"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_conversation_state_stage", table_name="conversation_state")
    op.drop_index("ix_conversation_state_tenant", table_name="conversation_state")
    op.drop_table("conversation_state")
