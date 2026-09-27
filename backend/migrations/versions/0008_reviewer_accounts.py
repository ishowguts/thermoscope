"""Per-person reviewer accounts (reviewer-accounts-v1, ADR-023).

Each reviewer signs in with a personal random token. Only the token's SHA-256 is stored; the
account, not the request body, names the reviewer. Accounts are never deleted and their identity
never changes (deactivate or rotate the token instead). Every new review must carry an account;
reviews saved before this revision (none exist in any known database) keep their typed name.
"""

from alembic import op

revision = "0008_reviewer_accounts"
down_revision = "0007_review_integrity"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE reviewers (
            id uuid PRIMARY KEY,
            name text NOT NULL CHECK (length(name) BETWEEN 2 AND 60),
            token_sha256 char(64) NOT NULL UNIQUE CHECK (token_sha256 ~ '^[0-9a-f]{64}$'),
            can_adjudicate boolean NOT NULL DEFAULT false,
            active boolean NOT NULL DEFAULT true,
            created_at timestamptz NOT NULL,
            token_issued_at timestamptz NOT NULL,
            deactivated_at timestamptz,
            CHECK (active OR deactivated_at IS NOT NULL)
        );
        CREATE UNIQUE INDEX ux_reviewers_name ON reviewers (lower(name));
        CREATE FUNCTION thermoscope_reviewer_guard() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP IN ('DELETE', 'TRUNCATE') THEN
                RAISE EXCEPTION 'reviewer accounts are never deleted (% refused); deactivate',
                    TG_OP USING ERRCODE = 'restrict_violation';
            END IF;
            IF NEW.id <> OLD.id OR NEW.name <> OLD.name OR NEW.created_at <> OLD.created_at THEN
                RAISE EXCEPTION 'reviewer identity is immutable; add a new account'
                    USING ERRCODE = 'restrict_violation';
            END IF;
            RETURN NEW;
        END $$;
        CREATE TRIGGER reviewers_guard BEFORE UPDATE OR DELETE ON reviewers
            FOR EACH ROW EXECUTE FUNCTION thermoscope_reviewer_guard();
        CREATE TRIGGER reviewers_no_truncate BEFORE TRUNCATE ON reviewers
            FOR EACH STATEMENT EXECUTE FUNCTION thermoscope_reviewer_guard();

        ALTER TABLE label_reviews ADD COLUMN reviewer_id uuid REFERENCES reviewers(id);
        -- NOT VALID: enforced for every new review, earlier rows (if any) are left as they are.
        ALTER TABLE label_reviews ADD CONSTRAINT label_reviews_signed_in
            CHECK (reviewer_id IS NOT NULL) NOT VALID;
        CREATE UNIQUE INDEX ux_label_reviews_account
            ON label_reviews (case_set_id, case_id, reviewer_id);
    """)


def downgrade():
    op.execute("""
        DROP INDEX ux_label_reviews_account;
        ALTER TABLE label_reviews DROP CONSTRAINT label_reviews_signed_in;
        ALTER TABLE label_reviews DROP COLUMN reviewer_id;
        DROP TRIGGER reviewers_no_truncate ON reviewers;
        DROP TRIGGER reviewers_guard ON reviewers;
        DROP FUNCTION thermoscope_reviewer_guard();
        DROP TABLE reviewers;
    """)
