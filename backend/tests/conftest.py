import os
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from sqlalchemy.engine import make_url
from thermoscope.config import Settings


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
