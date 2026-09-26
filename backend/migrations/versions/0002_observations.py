"""Add immutable observations, ingestion receipts and row quarantine."""

from alembic import op

revision = "0002_observations"
down_revision = "0001_source_snapshots"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE ingestion_runs (
            id uuid PRIMARY KEY,
            product text NOT NULL,
            bounds geometry(Polygon,4326) NOT NULL,
            start_date date NOT NULL,
            end_date date NOT NULL CHECK (end_date >= start_date AND end_date-start_date < 5),
            data_mode text NOT NULL CHECK (data_mode IN
                ('LIVE','HISTORICAL_REPLAY','SYNTHETIC_FIXTURE')),
            origin text NOT NULL CHECK (origin IN ('FILE','PROVIDER')),
            started_at timestamptz NOT NULL,
            received_at timestamptz,
            completed_at timestamptz,
            status text NOT NULL CHECK (status IN ('RUNNING','SUCCEEDED','PARTIAL','FAILED')),
            snapshot_id uuid REFERENCES source_snapshots(id),
            total_rows integer NOT NULL DEFAULT 0 CHECK (total_rows >= 0),
            accepted_rows integer NOT NULL DEFAULT 0 CHECK (accepted_rows >= 0),
            inserted_rows integer NOT NULL DEFAULT 0 CHECK (inserted_rows >= 0),
            rejected_rows integer NOT NULL DEFAULT 0 CHECK (rejected_rows >= 0),
            error_code text,
            CHECK (data_mode <> 'LIVE' OR origin = 'PROVIDER')
        );
        CREATE INDEX ix_runs_scope ON ingestion_runs(data_mode,product,started_at DESC);
        CREATE TABLE observations (
            id char(64) PRIMARY KEY CHECK (id ~ '^[0-9a-f]{64}$'),
            identity_version text NOT NULL DEFAULT 'firms-identity-v1',
            payload_sha256 char(64) NOT NULL,
            product text NOT NULL,
            acquired_at timestamptz NOT NULL,
            first_ingested_at timestamptz NOT NULL,
            geom geometry(Point,4326) NOT NULL,
            payload jsonb NOT NULL,
            CHECK (ST_X(geom) BETWEEN -180 AND 180 AND ST_Y(geom) BETWEEN -90 AND 90),
            CHECK (ST_X(geom) = (payload->>'longitude')::double precision),
            CHECK (ST_Y(geom) = (payload->>'latitude')::double precision),
            CHECK ((payload->>'frp_mw')::double precision >= 0),
            CHECK ((payload->>'brightness_i4_k')::double precision > 0),
            CHECK ((payload->>'brightness_i5_k')::double precision > 0),
            CHECK ((payload->>'scan_km')::double precision > 0),
            CHECK ((payload->>'track_km')::double precision > 0),
            CHECK (payload->>'source_confidence' IN ('l','n','h')),
            CHECK (first_ingested_at >= acquired_at)
        );
        CREATE INDEX ix_observations_geom ON observations USING gist(geom);
        CREATE INDEX ix_observations_time ON observations(product,acquired_at DESC,id);
        CREATE TABLE observation_receipts (
            run_id uuid NOT NULL REFERENCES ingestion_runs(id),
            row_number integer NOT NULL CHECK (row_number >= 2),
            observation_id char(64) NOT NULL REFERENCES observations(id),
            PRIMARY KEY (run_id,row_number)
        );
        CREATE INDEX ix_receipts_observation ON observation_receipts(observation_id,run_id);
        CREATE TABLE quarantined_rows (
            run_id uuid NOT NULL REFERENCES ingestion_runs(id),
            row_number integer NOT NULL,
            reason text NOT NULL,
            raw_row jsonb NOT NULL,
            PRIMARY KEY (run_id,row_number)
        );
    """)


def downgrade():
    op.execute("""
        DROP TABLE quarantined_rows;
        DROP TABLE observation_receipts;
        DROP TABLE observations;
        DROP TABLE ingestion_runs;
    """)
