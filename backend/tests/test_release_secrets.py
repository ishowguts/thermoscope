"""P08 release check: secrets never reach API responses, logs or command output, including when
the database is unreachable or a command fails. No database is needed: every connection goes to
a closed local port, with a recognisable fake password, FIRMS key and reviewer token."""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from thermoscope.config import Settings
from thermoscope.main import create_app

ROOT = Path(__file__).resolve().parents[2]
DB_SECRET = "Sentinel-db-pass-8Qx2"
KEY_SECRET = "SentinelFirmsKey0123456789abcdef"
TOKEN = "tsr_" + "Sentinel" * 5
SECRETS = (DB_SECRET, KEY_SECRET, TOKEN)
DEAD_URL = f"postgresql+psycopg://thermoscope:{DB_SECRET}@127.0.0.1:1/thermoscope_dev"
WINDOW = (
    "bbox=69.5,22,70.5,23&start_date=2026-09-01&end_date=2026-09-05&data_mode=HISTORICAL_REPLAY"
)
ID = "a" * 64


def assert_clean(text: str):
    for secret in SECRETS:
        assert secret not in text


@pytest.mark.parametrize("review_only", [False, True])
def test_api_responses_and_logs_never_contain_secrets(caplog, review_only):
    caplog.set_level(logging.DEBUG)
    settings = Settings(_env_file=None, database_url=DEAD_URL, firms_map_key=KEY_SECRET,
                        review_only=review_only)  # fmt: skip
    client = TestClient(create_app(settings), raise_server_exceptions=False)
    paths = [
        "/health/live", "/health/ready", "/api/v1/status", "/api/v1/catalog",
        f"/api/v1/observations?{WINDOW}",
        f"/api/v1/exports/observations.csv?{WINDOW}",
        f"/api/v1/exports/observations.geojson?{WINDOW}&rule_outputs=true",
        f"/api/v1/exports/observations/{ID}/evidence.geojson?data_mode=HISTORICAL_REPLAY",
        f"/api/v1/observations/{ID}/context?data_mode=HISTORICAL_REPLAY",
        f"/api/v1/observations/{ID}/assessment?data_mode=HISTORICAL_REPLAY",
        "/api/v1/annotation/me", "/api/v1/annotation/case-sets",
        "/api/v1/annotation/p05-pilot-v2/queue",
    ]  # fmt: skip
    for path in paths:
        response = client.get(path, headers={"Authorization": f"Bearer {TOKEN}"})
        assert response.status_code != 500, path  # every failure is handled
        assert_clean(response.text + json.dumps(dict(response.headers)))
    posted = client.post("/api/v1/annotation/p05-pilot-v2/reviews",
                         headers={"Authorization": f"Bearer {TOKEN}"},
                         json={"case_id": ID, "token": TOKEN})  # fmt: skip
    assert posted.status_code != 500
    assert_clean(posted.text)
    assert_clean(caplog.text)


def run(arguments: list[str], cwd: Path) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("DATABASE_URL", "FIRMS"))}
    env |= {
        "DATABASE_URL": DEAD_URL,
        "FIRMS_MAP_KEY": KEY_SECRET,
        "PYTHONPATH": str(ROOT / "backend"),
    }
    done = subprocess.run([sys.executable, *arguments], cwd=cwd, env=env, capture_output=True,
                          text=True, timeout=60)  # fmt: skip
    assert done.returncode != 0, arguments  # each of these fails without a database
    return done.stdout + done.stderr


def test_command_failures_never_print_secrets(tmp_path):
    saved = tmp_path / "window.csv"
    saved.write_text("latitude,longitude\n")
    script = str(ROOT / "scripts" / "demo_package.py")
    outputs = [
        run(["-m", "thermoscope.ingest", "import-file", "--file", str(saved), "--sha256", "0" * 64,
             "--start-date", "2026-01-01"], tmp_path),
        run(["-m", "thermoscope.ml_cli", "fingerprint", "--case-set", "p05-pilot-v2"], tmp_path),
        run(["-m", "thermoscope.ml_cli", "list-reviewers"], tmp_path),
        run([script, "build", "--out", str(tmp_path / "packages")], tmp_path),
        run([script, "load", "--package", str(tmp_path), "--database", "thermoscope_demo",
             "--create", "--offline"], tmp_path),
        run(["-m", "alembic", "-c", str(ROOT / "alembic.ini"), "upgrade", "head"], ROOT),
    ]  # fmt: skip
    for output in outputs:
        assert_clean(output)
