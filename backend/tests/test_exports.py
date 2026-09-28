"""P07 evidence exports and offline replay: formula-safe CSV, WGS84 GeoJSON with provenance,
request validation, blind-review withholding and the offline network guard (no database)."""

import csv
import importlib.util
import io
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from thermoscope.config import Settings
from thermoscope.exports import BASE_COLUMNS, RULE_COLUMNS, csv_cell, to_csv, to_geojson
from thermoscope.firms import IngestError
from thermoscope.main import create_app
from thermoscope.replay import _check_clean, content_digest

RECORD = {
    "observation_id": "a" * 64,
    "acquired_at_utc": "2026-09-09T09:05:00Z",
    "latitude": 22.92891,
    "longitude": 70.10848,
    "location_meaning": "PIXEL_CENTRE",
    "pixel_support_radius_m": 450.0,
    "pixel_support_basis": "SCAN_TRACK",
    "frp_mw": None,  # missing stays missing
    "brightness_i4_k": 342.86,
    "brightness_i5_k": 299.5,
    "scan_km": 0.5,
    "track_km": 0.49,
    "daynight": "D",
    "nasa_confidence": "n",
    "satellite": "N20",
    "sensor": '=HYPERLINK("http://example.invalid")',  # hostile text is neutralised
    "product": "VIIRS_NOAA20_NRT",
    "collection_version": "2.0NRT",
    "data_mode": "HISTORICAL_REPLAY",
    "historical_availability": "UNKNOWN",
    "raw_file_sha256": "b" * 64,
    "raw_row_number": 2,
    "ingestion_run_id": "00000000-0000-0000-0000-000000000001",
    "imported_at_utc": "2026-09-28T12:11:00Z",
    "source_attribution": "NASA FIRMS …",
}


def test_csv_cells_neutralise_formulas_but_keep_numbers():
    for hostile in ("=1+1", "+cmd", "-2+3", "@SUM(A1)", "\tx", "\rx", "\nx", "  =1+1",
                    "\u3000=1", "\uff1dSUM(A1)", "\uff0b1"):  # fmt: skip
        assert csv_cell(hostile) == "'" + hostile
    assert csv_cell(-3.5) == -3.5 and csv_cell(0) == 0 and csv_cell(None) == ""
    assert csv_cell(True) == "true" and csv_cell("N20") == "N20"


def test_csv_has_units_free_columns_status_and_empty_missing_values():
    rows = list(csv.DictReader(io.StringIO(to_csv([RECORD], include_rules=False))))
    assert list(rows[0]) == BASE_COLUMNS + ["learned_model", "human_validation"]
    assert rows[0]["frp_mw"] == ""  # never 0
    assert rows[0]["sensor"].startswith("'=")
    assert (rows[0]["learned_model"], rows[0]["human_validation"]) == ("NOT_SERVED", "PENDING")
    with_rules = to_csv([RECORD | dict.fromkeys(RULE_COLUMNS)], include_rules=True)
    assert all(column in with_rules.splitlines()[0] for column in RULE_COLUMNS)
    assert {"context_osm_as_of_utc", "context_attribution"} <= set(RULE_COLUMNS)


def test_geojson_uses_wgs84_longitude_latitude_and_describes_itself():
    collection = to_geojson([RECORD], {"observations": 1})
    feature = collection["features"][0]
    assert feature["geometry"] == {"type": "Point", "coordinates": [70.10848, 22.92891]}
    assert "latitude" not in feature["properties"] and feature["properties"]["frp_mw"] is None
    meta = collection["meta"]
    assert "WGS84" in meta["coordinates"] and "not a fire" in meta["geometry_meaning"]
    assert meta["units"]["frp_mw"].startswith("megawatts")
    assert meta["learned_model"].startswith("NOT_SERVED")
    assert meta["human_validation"].startswith("PENDING")


def test_export_requests_are_validated_and_withheld_on_a_review_server():
    base = {"bbox": "69.5,22,70.5,23", "start_date": "2026-09-01", "end_date": "2026-09-05"}
    client = TestClient(create_app(Settings(_env_file=None, database_url=None)))
    for suffix in ("csv", "geojson"):
        url = f"/api/v1/exports/observations.{suffix}"
        assert client.get(url, params=base | {"bbox": "60,10,70,20"}).status_code == 422
        assert client.get(url, params=base | {"end_date": "2026-10-15"}).status_code == 422
        assert client.get(url, params=base).status_code == 503  # no database configured
    status = client.get("/api/v1/status").json()
    assert status["human_validation"] == "PENDING_DEFERRED"
    assert status["classifier_status"].startswith("NOT_SERVED")
    review = TestClient(create_app(Settings(_env_file=None, database_url=None, review_only=True)))
    ruled = review.get("/api/v1/exports/observations.csv", params=base | {"rule_outputs": "true"})
    assert ruled.status_code == 403 and ruled.json()["code"] == "WITHHELD_ON_REVIEW_SERVER"
    evidence = review.get(f"/api/v1/exports/observations/{'a' * 64}/evidence.geojson")
    assert evidence.status_code == 403


def test_package_refuses_key_bearing_files_and_digests_content():
    with pytest.raises(IngestError, match="POSSIBLE_CREDENTIAL_IN_FILE"):
        _check_clean(b"see https://firms.modaps.eosdis.nasa.gov/api/area/csv/KEY/...", None)
    with pytest.raises(IngestError, match="POSSIBLE_CREDENTIAL_IN_FILE"):
        _check_clean(b"latitude,longitude\n1,2 fixture-secret\n", b"fixture-secret")
    _check_clean(b"latitude,longitude,bright_ti4\n", b"fixture-secret")
    files = [{"path": "b", "sha256": "2"}, {"path": "a", "sha256": "1"}]
    assert content_digest(files) == content_digest(list(reversed(files)))


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "demo_package.py"


def demo_script():
    spec = importlib.util.spec_from_file_location("demo_package", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_offline_guard_refuses_python_level_network_access():
    probe = f"""
import importlib.util, os, socket
spec = importlib.util.spec_from_file_location("demo_package", {str(SCRIPT)!r})
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
module.forbid_network()
server = socket.socket(); server.bind(("127.0.0.1", 0)); server.listen(1)
local = socket.create_connection(server.getsockname(), timeout=2); local.close()
udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp.sendto(b"x", ("127.0.0.1", server.getsockname()[1]))
attempts = [
    lambda: socket.create_connection(("198.51.100.7", 80), timeout=2),
    lambda: socket.create_connection(("example.org", 443), timeout=2),
    lambda: socket.create_connection(("2001:db8::1", 443), timeout=2),
    lambda: socket.gethostbyname("example.org"),
    lambda: socket.gethostbyname_ex("example.org"),
    lambda: socket.getaddrinfo("example.org", 443),
    lambda: udp.sendto(b"x", ("198.51.100.7", 53)),
]
for attempt in attempts:
    try:
        attempt()
        raise SystemExit("network reached")
    except OSError as error:
        assert "offline mode" in str(error), error
assert os.environ["HTTPS_PROXY"] == os.environ["GDAL_HTTP_PROXY"] == "http://127.0.0.1:9"
print("ok")
"""
    done = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True,
                          timeout=30)  # fmt: skip
    assert done.returncode == 0 and done.stdout.strip() == "ok", done.stderr[-500:]


def test_demo_script_never_loads_into_the_configured_database_or_store(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@127.0.0.1:1/thermoscope_dev")
    monkeypatch.setenv("OBJECT_STORE_LOCAL_PATH", str(tmp_path / "objects"))
    module = demo_script()
    for argv in (["load", "--package", "x"], ["serve"],
                 ["load", "--package", "x", "--database", "thermoscope_demo", "--objects",
                  str(tmp_path / "objects")]):  # fmt: skip
        with pytest.raises(SystemExit) as refused:
            module.main(argv)
        assert refused.value.code == 2  # argument error before any connection
    with pytest.raises(SystemExit, match="must not be the database configured"):
        module.use_database("thermoscope_dev", create=False)
    with pytest.raises(SystemExit, match="must look like"):
        module.use_database("postgres", create=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@db.example.org:5432/thermoscope")
    with pytest.raises(SystemExit, match="loopback"):
        module.use_database("thermoscope_demo", create=False)
