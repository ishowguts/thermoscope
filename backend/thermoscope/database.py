from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from thermoscope.config import Settings

SCHEMA_REVISION = "0008_reviewer_accounts"


API_STATEMENT_TIMEOUT_MS = 2000
# Offline batch jobs (event building, case features, training) scan whole regions.
BATCH_STATEMENT_TIMEOUT_MS = 600_000


@contextmanager
def batch_engine(settings: Settings):
    with database_engine(settings, statement_timeout_ms=BATCH_STATEMENT_TIMEOUT_MS) as engine:
        yield engine


@contextmanager
def database_engine(settings: Settings, statement_timeout_ms: int = API_STATEMENT_TIMEOUT_MS):
    if settings.database_url is None:
        raise ValueError("database_not_configured")
    engine = create_engine(
        settings.database_url.get_secret_value(),
        connect_args={
            "connect_timeout": 3,
            "options": f"-c statement_timeout={int(statement_timeout_ms)}",
        },
        hide_parameters=True,
        pool_pre_ping=True,
    )
    try:
        yield engine
    finally:
        engine.dispose()


def check_readiness(settings: Settings) -> dict[str, str]:
    checks = {"database": "not_configured", "postgis": "not_checked", "schema": "not_checked"}
    if settings.database_url is None:
        return checks
    checks["database"] = "unavailable"
    try:
        with database_engine(settings) as engine, engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            checks["database"] = "ok"
            checks["postgis"] = "unavailable"
            conn.execute(text("SELECT PostGIS_Version()"))
            checks["postgis"] = "ok"
            checks["schema"] = "migration_required"
            revision = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            if revision == SCHEMA_REVISION:
                checks["schema"] = "ok"
    except SQLAlchemyError:
        pass  # Connection strings and driver exceptions never reach the health response.
    return checks
