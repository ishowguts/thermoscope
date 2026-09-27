"""Add dated land-cover summaries over each observation's approximate pixel area."""

from alembic import op

revision = "0005_landcover"
down_revision = "0004_events_sites"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE landcover_summaries (
            observation_id char(64) NOT NULL REFERENCES observations(id),
            product text NOT NULL,
            summary_version text NOT NULL,
            run_id uuid NOT NULL,
            tile_id text NOT NULL,
            source text NOT NULL,
            window_sha256 char(64) NOT NULL CHECK (window_sha256 ~ '^[0-9a-f]{64}$'),
            chip_object text NOT NULL,
            tile_edge_clipped boolean NOT NULL,
            support_basis text NOT NULL,
            support jsonb NOT NULL,
            context jsonb NOT NULL,
            status text NOT NULL CHECK (status IN ('OK','INSUFFICIENT')),
            extracted_at timestamptz NOT NULL,
            CHECK ((support->>'valid_fraction')::double precision BETWEEN 0 AND 1),
            CHECK ((context->>'valid_fraction')::double precision BETWEEN 0 AND 1),
            PRIMARY KEY (observation_id,product,summary_version)
        );
    """)


def downgrade():
    op.execute("DROP TABLE landcover_summaries;")
