"""P05: frozen case sets and splits, blind append-only reviews, registry evidence, models."""

from alembic import op

revision = "0006_labels_models"
down_revision = "0005_landcover"
branch_labels = None
depends_on = None

SOURCE_LABELS = "'INDUSTRIAL','VEGETATION_FIRE','AGRICULTURAL_BURN','OTHER','UNRESOLVED'"


def upgrade():
    op.execute(f"""
        CREATE TABLE case_sets (
            id uuid PRIMARY KEY,
            name text NOT NULL UNIQUE,
            data_mode text NOT NULL,
            case_version text NOT NULL,
            split_policy jsonb NOT NULL,
            event_runs jsonb NOT NULL,
            case_count integer NOT NULL CHECK (case_count >= 0),
            manifest_sha256 char(64) NOT NULL CHECK (manifest_sha256 ~ '^[0-9a-f]{{64}}$'),
            created_at timestamptz NOT NULL
        );
        CREATE TABLE label_cases (
            case_set_id uuid NOT NULL REFERENCES case_sets(id),
            id char(64) NOT NULL CHECK (id ~ '^[0-9a-f]{{64}}$'),
            event_run_id uuid NOT NULL,
            event_id char(64) NOT NULL,
            site_id char(64) NOT NULL,
            split_group text NOT NULL,
            split text NOT NULL CHECK (split IN ('TRAIN','VALIDATION','TEST')),
            forward_period text NOT NULL CHECK (forward_period IN ('BEFORE','AFTER')),
            region_id text NOT NULL,
            as_of timestamptz NOT NULL,
            started_at timestamptz NOT NULL,
            observation_count integer NOT NULL CHECK (observation_count > 0),
            representative_observation_id char(64) NOT NULL REFERENCES observations(id),
            geom geometry(Point,4326) NOT NULL,
            review_slots smallint NOT NULL CHECK (review_slots IN (1,2)),
            review_rank integer NOT NULL,
            PRIMARY KEY (case_set_id,id)
        );
        CREATE INDEX ix_label_cases_queue ON label_cases(case_set_id,review_rank);
        CREATE TABLE label_reviews (
            id uuid PRIMARY KEY,
            case_set_id uuid NOT NULL,
            case_id char(64) NOT NULL,
            reviewer text NOT NULL CHECK (length(reviewer) BETWEEN 2 AND 60),
            role text NOT NULL CHECK (role IN ('REVIEWER','ADJUDICATOR')),
            source_label text NOT NULL CHECK (source_label IN ({SOURCE_LABELS})),
            industrial_subtype text,
            certainty text NOT NULL CHECK (certainty IN ('HIGH','MEDIUM','LOW')),
            evidence jsonb NOT NULL,
            evidence_date date,
            notes text CHECK (length(notes) <= 2000),
            blind boolean NOT NULL,
            reviewed_at timestamptz NOT NULL,
            FOREIGN KEY (case_set_id,case_id) REFERENCES label_cases(case_set_id,id),
            UNIQUE (case_set_id,case_id,reviewer,role)
        );
        CREATE TABLE registry_sources (
            id text PRIMARY KEY,
            name text NOT NULL,
            version text NOT NULL,
            license text NOT NULL,
            attribution text NOT NULL,
            url text NOT NULL,
            content_sha256 char(64) NOT NULL,
            data_year integer,
            retrieved_at timestamptz NOT NULL,
            imported_at timestamptz NOT NULL
        );
        CREATE TABLE registry_facilities (
            source_id text NOT NULL REFERENCES registry_sources(id),
            record_id text NOT NULL,
            name text,
            category text NOT NULL,
            fuel text,
            capacity_mw double precision,
            commissioning_year double precision,
            geom geometry(Point,4326) NOT NULL,
            PRIMARY KEY (source_id,record_id)
        );
        CREATE INDEX ix_registry_geog ON registry_facilities USING gist((geom::geography));
        CREATE TABLE case_features (
            case_set_id uuid NOT NULL,
            case_id char(64) NOT NULL,
            feature_version text NOT NULL,
            features jsonb NOT NULL,
            weak_label text,
            weak_rule text,
            silver_label text,
            silver_evidence jsonb,
            nasa_type_majority integer,
            sha256 char(64) NOT NULL,
            computed_at timestamptz NOT NULL,
            PRIMARY KEY (case_set_id,case_id,feature_version),
            FOREIGN KEY (case_set_id,case_id) REFERENCES label_cases(case_set_id,id)
        );
        CREATE TABLE model_versions (
            id uuid PRIMARY KEY,
            case_set_id uuid NOT NULL REFERENCES case_sets(id),
            algorithm text NOT NULL,
            feature_version text NOT NULL,
            label_policy text NOT NULL,
            labels_sha256 char(64) NOT NULL,
            artifact_dir text NOT NULL,
            artifact_sha256 char(64) NOT NULL,
            status text NOT NULL CHECK (status IN
                ('DRY_RUN_NOT_EVIDENCE','EVALUATED_NOT_PROMOTED','PROMOTED','INSUFFICIENT_LABELS')),
            metrics jsonb NOT NULL,
            created_at timestamptz NOT NULL
        );
    """)


def downgrade():
    op.execute("""
        DROP TABLE model_versions;
        DROP TABLE case_features;
        DROP TABLE registry_facilities;
        DROP TABLE registry_sources;
        DROP TABLE label_reviews;
        DROP TABLE label_cases;
        DROP TABLE case_sets;
    """)
