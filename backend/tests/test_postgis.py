"""Real database checks run only against a database this test creates and owns."""

import os
from uuid import uuid4

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from psycopg import sql
from sqlalchemy.engine import make_url
from thermoscope.config import Settings
from thermoscope.main import create_app

pytestmark = pytest.mark.integration


@pytest.fixture
def test_database(monkeypatch):
    if os.environ.get("THERMOSCOPE_RUN_DB_TESTS") != "1":
        pytest.skip("Run make integration to create a disposable local test database")
    config = Settings()
    if config.database_url is None:
        pytest.fail("Configure the local database first")
    url = make_url(config.database_url.get_secret_value())
    if url.host not in {"127.0.0.1", "localhost"}:
        pytest.fail(
            "Integration tests require a loopback database; refusing remote admin operations"
        )
    name = f"thermoscope_test_{uuid4().hex}"
    admin_url = url.set(drivername="postgresql", database="postgres")
    with psycopg.connect(admin_url.render_as_string(hide_password=False), autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name)))
        try:
            db_url = url.set(database=name)
            monkeypatch.setenv("DATABASE_URL", db_url.render_as_string(hide_password=False))
            yield db_url
        finally:
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


def test_migration_distance_constraints_and_readiness(test_database):
    config = Config("alembic.ini")
    client = TestClient(create_app(Settings()))
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 503
    command.upgrade(config, "head")
    assert client.get("/health/ready").json()["checks"] == {
        "database": "ok",
        "postgis": "ok",
        "schema": "ok",
    }
    with psycopg.connect(
        test_database.set(drivername="postgresql").render_as_string(hide_password=False),
        autocommit=True,
    ) as conn:
        distance = conn.execute(
            "SELECT ST_Distance(ST_SetSRID(ST_Point(0,0),4326)::geography, "
            "ST_SetSRID(ST_Point(1,0),4326)::geography)"
        ).fetchone()[0]
        assert distance == pytest.approx(111319.49, abs=1)
        insert = (
            "INSERT INTO source_snapshots "
            "(id, provider, product, content_sha256, data_mode, ingested_at) "
            "VALUES (%s, 'TEST_FIXTURE', 'fixture', %s, %s, now())"
        )
        conn.execute(insert, (uuid4(), "0" * 64, "SYNTHETIC_FIXTURE"))
        with pytest.raises(psycopg.errors.UniqueViolation):
            conn.execute(insert, (uuid4(), "0" * 64, "SYNTHETIC_FIXTURE"))
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute(insert, (uuid4(), "1" * 64, "MADE_UP_MODE"))
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute(insert, (uuid4(), "bad-hash", "SYNTHETIC_FIXTURE"))
    command.downgrade(config, "base")
    assert client.get("/health/ready").status_code == 503
    command.upgrade(config, "head")
    assert client.get("/health/ready").status_code == 200
    # This fixture owns its empty database. Never use downgrade on the development data volume.
