"""Add dated OSM facility snapshots, context runs and element quarantine."""

from alembic import op

revision = "0003_facility_context"
down_revision = "0002_observations"
branch_labels = None
depends_on = None

FACILITY_TYPES = "'REFINERY','PETROCHEMICAL','STEEL','POWER','LNG','MINE','OTHER','UNKNOWN'"


def upgrade():
    op.execute(f"""
        CREATE TABLE facility_snapshots (
            id uuid PRIMARY KEY,
            provider text NOT NULL CHECK (provider IN ('OSM_OVERPASS','TEST_FIXTURE')),
            query_version text NOT NULL,
            query_sha256 char(64) NOT NULL CHECK (query_sha256 ~ '^[0-9a-f]{{64}}$'),
            type_map_version text NOT NULL,
            region_id text NOT NULL,
            bounds geometry(Polygon,4326) NOT NULL,
            content_sha256 char(64) NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{{64}}$'),
            osm_base_at timestamptz NOT NULL,
            first_received_at timestamptz NOT NULL CHECK (first_received_at >= osm_base_at),
            element_count integer NOT NULL CHECK (element_count >= 0),
            facility_count integer NOT NULL CHECK (facility_count >= 0),
            license text NOT NULL,
            attribution text NOT NULL,
            UNIQUE (provider,content_sha256)
        );
        CREATE INDEX ix_facility_snapshots_bounds ON facility_snapshots USING gist(bounds);
        CREATE TABLE context_runs (
            id uuid PRIMARY KEY,
            provider text NOT NULL,
            region_id text NOT NULL,
            bounds geometry(Polygon,4326) NOT NULL,
            query_sha256 char(64) NOT NULL,
            origin text NOT NULL CHECK (origin IN ('FILE','PROVIDER')),
            endpoint text,
            started_at timestamptz NOT NULL,
            received_at timestamptz,
            completed_at timestamptz,
            status text NOT NULL CHECK (status IN ('RUNNING','SUCCEEDED','PARTIAL','FAILED')),
            snapshot_id uuid REFERENCES facility_snapshots(id),
            total_elements integer NOT NULL DEFAULT 0 CHECK (total_elements >= 0),
            accepted_elements integer NOT NULL DEFAULT 0 CHECK (accepted_elements >= 0),
            rejected_elements integer NOT NULL DEFAULT 0 CHECK (rejected_elements >= 0),
            error_code text
        );
        CREATE TABLE facilities (
            snapshot_id uuid NOT NULL REFERENCES facility_snapshots(id),
            osm_type text NOT NULL CHECK (osm_type IN ('node','way','relation')),
            osm_id bigint NOT NULL CHECK (osm_id > 0),
            osm_version integer,
            osm_timestamp timestamptz,
            name text,
            facility_type text NOT NULL CHECK (facility_type IN ({FACILITY_TYPES})),
            primary_tag text NOT NULL,
            build text NOT NULL CHECK (build IN ('POINT','WAY_POLYGON','RELATION_AREA')),
            tags jsonb NOT NULL,
            geom geometry(Geometry,4326) NOT NULL,
            CHECK (ST_IsValid(geom) AND NOT ST_IsEmpty(geom)),
            CHECK (GeometryType(geom) IN ('POINT','POLYGON','MULTIPOLYGON')),
            PRIMARY KEY (snapshot_id,osm_type,osm_id)
        );
        CREATE INDEX ix_facilities_geom ON facilities USING gist(geom);
        CREATE INDEX ix_facilities_geog ON facilities USING gist((geom::geography));
        CREATE TABLE context_quarantine (
            run_id uuid NOT NULL REFERENCES context_runs(id),
            osm_type text NOT NULL,
            osm_id bigint NOT NULL,
            reason text NOT NULL,
            PRIMARY KEY (run_id,osm_type,osm_id)
        );
    """)


def downgrade():
    op.execute("""
        DROP TABLE context_quarantine;
        DROP TABLE facilities;
        DROP TABLE context_runs;
        DROP TABLE facility_snapshots;
    """)
