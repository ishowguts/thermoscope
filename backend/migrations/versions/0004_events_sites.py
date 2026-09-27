"""Add versioned event/site runs, deterministic memberships and cross-run lineage."""

from alembic import op

revision = "0004_events_sites"
down_revision = "0003_facility_context"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE event_runs (
            id uuid PRIMARY KEY,
            algorithm_version text NOT NULL,
            params jsonb NOT NULL,
            params_sha256 char(64) NOT NULL CHECK (params_sha256 ~ '^[0-9a-f]{64}$'),
            data_mode text NOT NULL CHECK (data_mode IN
                ('LIVE','HISTORICAL_REPLAY','SYNTHETIC_FIXTURE')),
            product text NOT NULL,
            region_id text NOT NULL,
            bounds geometry(Polygon,4326) NOT NULL,
            input_count integer NOT NULL CHECK (input_count >= 0),
            input_sha256 char(64) NOT NULL CHECK (input_sha256 ~ '^[0-9a-f]{64}$'),
            latest_input_acquired_at timestamptz,
            previous_run_id uuid REFERENCES event_runs(id),
            late_arrivals integer NOT NULL DEFAULT 0 CHECK (late_arrivals >= 0),
            earliest_late_arrival_at timestamptz,
            merges_in_run integer NOT NULL DEFAULT 0 CHECK (merges_in_run >= 0),
            ambiguous_links integer NOT NULL DEFAULT 0 CHECK (ambiguous_links >= 0),
            event_count integer NOT NULL CHECK (event_count >= 0),
            site_count integer NOT NULL CHECK (site_count >= 0),
            created_at timestamptz NOT NULL
        );
        CREATE INDEX ix_event_runs_scope
            ON event_runs(region_id,data_mode,product,algorithm_version,created_at DESC);
        CREATE TABLE sites (
            run_id uuid NOT NULL REFERENCES event_runs(id),
            id char(64) NOT NULL CHECK (id ~ '^[0-9a-f]{64}$'),
            first_seen_at timestamptz NOT NULL,
            last_seen_at timestamptz NOT NULL CHECK (last_seen_at >= first_seen_at),
            event_count integer NOT NULL CHECK (event_count > 0),
            observation_count integer NOT NULL CHECK (observation_count > 0),
            diameter_m double precision NOT NULL CHECK (diameter_m >= 0),
            geom geometry(Geometry,4326) NOT NULL,
            PRIMARY KEY (run_id,id)
        );
        CREATE TABLE events (
            run_id uuid NOT NULL REFERENCES event_runs(id),
            id char(64) NOT NULL CHECK (id ~ '^[0-9a-f]{64}$'),
            site_id char(64) NOT NULL,
            started_at timestamptz NOT NULL,
            ended_at timestamptz NOT NULL CHECK (ended_at >= started_at),
            observation_count integer NOT NULL CHECK (observation_count > 0),
            overpass_count integer NOT NULL CHECK (overpass_count > 0),
            max_frp_mw double precision CHECK (max_frp_mw >= 0),
            diameter_m double precision NOT NULL CHECK (diameter_m >= 0),
            ambiguous_links integer NOT NULL DEFAULT 0 CHECK (ambiguous_links >= 0),
            geom geometry(Geometry,4326) NOT NULL,
            PRIMARY KEY (run_id,id),
            FOREIGN KEY (run_id,site_id) REFERENCES sites(run_id,id)
        );
        CREATE INDEX ix_events_geom ON events USING gist(geom);
        CREATE INDEX ix_events_time ON events(run_id,started_at,ended_at);
        CREATE TABLE event_observations (
            run_id uuid NOT NULL,
            event_id char(64) NOT NULL,
            observation_id char(64) NOT NULL REFERENCES observations(id),
            PRIMARY KEY (run_id,observation_id),
            FOREIGN KEY (run_id,event_id) REFERENCES events(run_id,id)
        );
        CREATE INDEX ix_event_observations_event ON event_observations(run_id,event_id);
        CREATE TABLE event_lineage (
            run_id uuid NOT NULL,
            event_id char(64) NOT NULL,
            previous_run_id uuid NOT NULL REFERENCES event_runs(id),
            previous_event_id char(64) NOT NULL,
            relation text NOT NULL CHECK (relation IN
                ('SAME','GREW','SHRANK','MERGED','SPLIT','CHANGED')),
            shared_observations integer NOT NULL CHECK (shared_observations > 0),
            PRIMARY KEY (run_id,event_id,previous_event_id),
            FOREIGN KEY (run_id,event_id) REFERENCES events(run_id,id),
            FOREIGN KEY (previous_run_id,previous_event_id) REFERENCES events(run_id,id)
        );
    """)


def downgrade():
    op.execute("""
        DROP TABLE event_lineage;
        DROP TABLE event_observations;
        DROP TABLE events;
        DROP TABLE sites;
        DROP TABLE event_runs;
    """)
