from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from thermoscope.config import Settings

SCHEMA_REVISION = "0002_observations"


@contextmanager
def database_engine(settings: Settings):
    if settings.database_url is None:
        raise ValueError("database_not_configured")
    engine = create_engine(
        settings.database_url.get_secret_value(),
        connect_args={"connect_timeout": 3, "options": "-c statement_timeout=2000"},
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
