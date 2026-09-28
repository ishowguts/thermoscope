"""P08 release check: secrets never reach API responses, logs, tracebacks or command output,
including when the database is unreachable, a provider fails or a command fails. No database is
needed: every connection goes to a closed local port, with a recognisable fake database password,
a well-formed fake FIRMS key and a well-formed fake reviewer token, so each request really reaches
the authentication, database or provider step it is meant to test."""

import json
import logging
import os
import subprocess
import sys
import traceback
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest
from fastapi.testclient import TestClient
from test_firms import window
from thermoscope.config import Settings
from thermoscope.firms import IngestError, fetch_csv
from thermoscope.main import create_app
from thermoscope.reviewers import TOKEN as TOKEN_FORMAT

ROOT = Path(__file__).resolve().parents[2]
DB_SECRET = "Sentinel-db-pass-8Qx2"
KEY_SECRET = "SentinelFirmsKey0123456789abcdef"  # the 32-character form FIRMS keys take
TOKEN = "tsr_" + ("Sentinel" * 6)[:43]  # the form personal reviewer tokens take
SECRETS = (DB_SECRET, KEY_SECRET, TOKEN)
DEAD_URL = f"postgresql+psycopg://thermoscope:{DB_SECRET}@127.0.0.1:1/thermoscope_dev"
WINDOW = (
    "bbox=69.5,22,70.5,23&start_date=2026-09-01&end_date=2026-09-05&data_mode=HISTORICAL_REPLAY"
)
ID = "a" * 64
REVIEW = {"case_id": ID, "source_label": "UNRESOLVED", "certainty": "LOW",
          "expected_role": "REVIEWER"}  # fmt: skip
# path -> status on a normal server, status on a blind-review server (503 = reached the database)
EXPECTED = {
    "/health/live": (200, 200),
    "/health/ready": (503, 503),
    "/api/v1/status": (200, 200),
    "/api/v1/catalog": (503, 503),
    f"/api/v1/observations?{WINDOW}": (503, 503),
    f"/api/v1/exports/observations.csv?{WINDOW}": (503, 503),
    f"/api/v1/exports/observations.geojson?{WINDOW}&rule_outputs=true": (503, 403),
    f"/api/v1/exports/observations/{ID}/evidence.geojson?data_mode=HISTORICAL_REPLAY": (503, 403),
    f"/api/v1/observations/{ID}/context?data_mode=HISTORICAL_REPLAY": (503, 503),
    f"/api/v1/observations/{ID}/assessment?data_mode=HISTORICAL_REPLAY": (503, 403),
    "/api/v1/annotation/me": (503, 503),
    "/api/v1/annotation/case-sets": (503, 503),
    "/api/v1/annotation/p05-pilot-v2/queue": (503, 503),
}


def assert_clean(text: str):
    for secret in SECRETS:
        assert secret not in text


def test_fixtures_have_the_real_secret_formats():
    assert TOKEN_FORMAT.fullmatch(TOKEN) and len(KEY_SECRET) == 32 and KEY_SECRET.isalnum()


@pytest.mark.parametrize("review_only", [False, True])
def test_api_responses_and_logs_never_contain_secrets(caplog, review_only):
    caplog.set_level(logging.DEBUG)
    settings = Settings(_env_file=None, database_url=DEAD_URL, firms_map_key=KEY_SECRET,
                        review_only=review_only)  # fmt: skip
    client = TestClient(create_app(settings), raise_server_exceptions=False)
    auth = {"Authorization": f"Bearer {TOKEN}"}
    for path, statuses in EXPECTED.items():
        response = client.get(path, headers=auth)
        assert response.status_code == statuses[review_only], path
        assert_clean(response.text + json.dumps(dict(response.headers)))
    posted = client.post("/api/v1/annotation/p05-pilot-v2/reviews", headers=auth, json=REVIEW)
    assert (posted.status_code, posted.json()["code"]) == (503, "DATA_UNAVAILABLE")
    assert_clean(posted.text)
    assert_clean(caplog.text)


def test_provider_failures_never_expose_the_firms_key(caplog):
    caplog.set_level(logging.DEBUG)
    endpoint = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{KEY_SECRET}/x"

    class Failing:
        def __init__(self, error):
            self.error = error

        def open(self, request, timeout):
            assert KEY_SECRET in request.full_url  # the key really is in the request
            raise self.error

    for error in (URLError(f"failed {endpoint}"),
                  HTTPError(endpoint, 503, f"busy {endpoint}", {}, None),
                  HTTPError(endpoint, 401, "denied", {}, None)):  # fmt: skip
        with pytest.raises(IngestError) as caught:
            fetch_csv(KEY_SECRET, window(), opener=Failing(error), sleep=lambda _: None)
        assert_clean(str(caught.value) + "".join(traceback.format_exception(caught.value)))
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
    output = done.stdout + done.stderr
    assert done.returncode == 1, (arguments, output[-300:])  # a runtime failure, not a usage error
    assert any(sign in output for sign in ("Connection refused", "DATABASE_UNAVAILABLE",
                                           "CONFIGURATION_OR_DEPENDENCY_ERROR"))  # fmt: skip
    return output


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
