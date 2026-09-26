"""Real database checks run only against a database this test creates and owns."""

from uuid import uuid4

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from thermoscope.config import Settings
from thermoscope.main import create_app

pytestmark = pytest.mark.integration


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
