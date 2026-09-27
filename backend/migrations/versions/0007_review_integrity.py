"""P05 reconciliation: database-enforced immutability of frozen case sets, reviews, features
and model records, and one review per person per case regardless of letter case."""

from alembic import op

revision = "0007_review_integrity"
down_revision = "0006_labels_models"
branch_labels = None
depends_on = None

FROZEN = ("case_sets", "label_cases", "label_reviews", "case_features", "model_versions")


def upgrade():
    op.execute("""
        CREATE FUNCTION thermoscope_refuse_change() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'P05 record in % is immutable (% refused); create a new version',
                TG_TABLE_NAME, TG_OP USING ERRCODE = 'restrict_violation';
        END $$;
    """)
    for table in FROZEN:
        op.execute(f"""
            CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table}
                FOR EACH ROW EXECUTE FUNCTION thermoscope_refuse_change();
            CREATE TRIGGER {table}_no_truncate BEFORE TRUNCATE ON {table}
                FOR EACH STATEMENT EXECUTE FUNCTION thermoscope_refuse_change();
        """)
    op.execute("""
        CREATE UNIQUE INDEX ux_label_reviews_person
            ON label_reviews (case_set_id, case_id, lower(reviewer));
    """)


def downgrade():
    op.execute("DROP INDEX ux_label_reviews_person")
    for table in reversed(FROZEN):
        op.execute(f"""
            DROP TRIGGER {table}_no_truncate ON {table};
            DROP TRIGGER {table}_immutable ON {table};
        """)
    op.execute("DROP FUNCTION thermoscope_refuse_change()")
