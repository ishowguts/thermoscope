"""Create the source provenance ledger and enable PostGIS."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0001_source_snapshots"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.create_table(
        "source_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.Text, nullable=False),
        sa.Column("product", sa.Text, nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("data_mode", sa.Text, nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("content_sha256 ~ '^[0-9a-f]{64}$'", name="ck_snapshot_hash"),
        sa.CheckConstraint(
            "data_mode IN ('LIVE','HISTORICAL_REPLAY','SYNTHETIC_FIXTURE')",
            name="ck_snapshot_mode",
        ),
        sa.UniqueConstraint("provider", "product", "content_sha256", name="uq_source_content"),
    )


def downgrade():
    op.drop_table("source_snapshots")
    # PostGIS may serve other schemas; rollback never removes the shared extension.
