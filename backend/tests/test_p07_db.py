"""P07 against real disposable PostGIS databases: the offline demo package round trip (build,
verify, tamper checks, network-refusing load into a second database, idempotent reload) and the
evidence exports (bounds, missing data, provenance, attribution, withholding). Fixture data only;
no labels, reviews or models are created."""

import csv
import hashlib
import importlib.util
import json
import os
import shutil
import socket
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from psycopg import sql
from pydantic import SecretStr
from sqlalchemy import text
from test_context import fixture_osm
from test_firms import HEADER, ROW, fixture_csv, window
from test_landcover import synthetic_raster
from thermoscope import exports
from thermoscope.assessment import observation_assessment
from thermoscope.config import DataMode, Settings
from thermoscope.context import observation_context
from thermoscope.context_ingestion import ingest_osm
from thermoscope.database import database_engine
from thermoscope.firms import IngestError
from thermoscope.ingestion import ingest
from thermoscope.landcover import extract_landcover
from thermoscope.main import create_app
from thermoscope.regions import Bounds, Window
from thermoscope.replay import (
    build_package,
    content_digest,
    load_package,
    restore_landcover,
    verify_package,
)

pytestmark = pytest.mark.integration

A = ROW  # inside the fixture refinery, next to a flare, on the synthetic land-cover raster
C = ROW.replace("22.3,69.8", "22.3,69.83")  # near a mapped industrial area, off the raster
D = ROW.replace("22.3,69.8", "22.8,69.6").replace(",0,D", ",,D")  # nothing mapped, FRP missing
# A standard-product (SP) detection on the land-cover raster: history input, not listed in the UI
SP = (
    ROW.rstrip("\n")
    .replace("22.3,69.8", "22.305,69.805")
    .replace("2.0NRT", "2")
    .replace("2026-01-02", "2025-12-30")
    + ",2\n"
)  # before the NRT window, like the archive
MODE = DataMode.HISTORICAL_REPLAY
RETRIEVED = datetime(2026, 1, 5, 6, tzinfo=UTC)
ENDPOINT = "https://overpass.fixture.invalid/api/interpreter"
WINDOW = {"bbox": "69.5,22,70.5,23", "start_date": "2026-01-01", "end_date": "2026-01-03",
          "data_mode": MODE.value}  # fmt: skip


def migrate(monkeypatch, url):
    monkeypatch.setenv("DATABASE_URL", url.render_as_string(hide_password=False))
    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture
def source(test_database, tmp_path):
    """A workspace-like database holding one replayed FIRMS file, OSM and land cover."""
    command.upgrade(Config("alembic.ini"), "head")
    settings = Settings(object_store_local_path=tmp_path / "source-objects", firms_map_key=None,
                        review_only=False)  # fmt: skip
    assert ingest(settings, window(), MODE, payload=fixture_csv(A, C, D))["status"] == "SUCCEEDED"
    sp_window = Window(product="VIIRS_NOAA20_SP", bounds=Bounds.parse("69.5,22,70.5,23"),
                       start_date="2025-12-29", days=3)  # fmt: skip
    sp_payload = (HEADER.rstrip("\n") + ",type\n" + SP).encode()
    assert ingest(settings, sp_window, MODE, payload=sp_payload)["status"] == "SUCCEEDED"
    osm = fixture_osm()
    osm_dir = tmp_path / "osm"
    osm_dir.mkdir()
    (osm_dir / "jamnagar-osm-20260105T060000Z.json").write_bytes(osm)
    (osm_dir / "jamnagar-osm-20260105T060000Z.json.meta.json").write_text(
        json.dumps({
            "content_sha256": hashlib.sha256(osm).hexdigest(), "endpoint": ENDPOINT,
            "http_status": 200, "method": "POST", "query_sha256": "0" * 64,
            "received_at": RETRIEVED.isoformat().replace("+00:00", "Z"), "region": "jamnagar",
        })
    )  # fmt: skip
    ingest_osm(settings, "jamnagar", payload=osm, expected_sha256=hashlib.sha256(osm).hexdigest(),
               retrieved_at=RETRIEVED, endpoint=ENDPOINT)  # fmt: skip
    raster = synthetic_raster(tmp_path / "wc.tif")
    extract_landcover(settings, "jamnagar", MODE, resolve=lambda tile: raster)
    return settings, osm_dir


@pytest.fixture
def target(test_database, monkeypatch, tmp_path):
    """A second, empty database on the same loopback server."""
    name = f"thermoscope_test_{uuid4().hex}"
    admin = test_database.set(drivername="postgresql", database="postgres")
    with psycopg.connect(admin.render_as_string(hide_password=False), autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name)))
    try:
        url = test_database.set(database=name)
        migrate(monkeypatch, url)
        monkeypatch.setenv("DATABASE_URL", test_database.render_as_string(hide_password=False))
        yield Settings(
            database_url=url.render_as_string(hide_password=False),
            object_store_local_path=tmp_path / "target-objects",
            firms_map_key=None,
        )
    finally:
        with psycopg.connect(admin.render_as_string(hide_password=False), autocommit=True) as conn:
            conn.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


def offline(monkeypatch):
    """Apply the demo script's network guard for this test only."""
    script = Path(__file__).resolve().parents[2] / "scripts" / "demo_package.py"
    spec = importlib.util.spec_from_file_location("demo_package", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for owner, attribute in ((socket.socket, "connect"), (socket.socket, "connect_ex"),
                             (socket.socket, "sendto"), (socket.socket, "sendmsg"),
                             (socket, "getaddrinfo"), (socket, "gethostbyname"),
                             (socket, "gethostbyname_ex")):  # fmt: skip
        monkeypatch.setattr(owner, attribute, getattr(owner, attribute))  # restored afterwards
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy",
                 "all_proxy", "GDAL_HTTP_PROXY", "NO_PROXY", "no_proxy"):  # fmt: skip
        monkeypatch.setenv(name, os.environ.get(name, ""))  # restored (or removed) afterwards
    module.forbid_network()
    with pytest.raises(OSError, match="offline mode"):
        socket.create_connection(("198.51.100.7", 443), timeout=1)


def observation_ids(settings):
    with database_engine(settings) as engine, engine.connect() as conn:
        return conn.execute(text("SELECT id FROM observations ORDER BY id")).scalars().all()


def labels(settings, observation_id):
    result = observation_assessment(settings, observation_id, MODE, None, "RETROSPECTIVE")
    context = observation_context(settings, observation_id, MODE)
    return (
        [result[k]["label"] for k in ("source", "behaviour", "priority")],
        result["missing_or_limited"],
        {k: v for k, v in context["association"].items() if k != "candidates"},
        (context["land_cover"] or {}).get("support"),
    )


def test_demo_package_round_trip_is_verified_offline_and_repeatable(
    source, target, tmp_path, monkeypatch
):
    settings, osm_dir = source
    out = tmp_path / "packages"
    built = build_package(settings, out, "fixture-demo", ["jamnagar"], [], osm_dir)
    assert built["files"]["OSM_OVERPASS_JSON"] == 1
    assert built["files"]["FIRMS_CSV"] == 2  # NRT and SP windows
    assert built["files"]["WORLDCOVER_SUMMARIES"] == 1 and built["files"]["WORLDCOVER_CHIP"] >= 1
    package = out / "fixture-demo"
    manifest = json.loads((package / "manifest.json").read_text())
    summarized = {r["observation_id"] for r in
                  json.loads((package / "worldcover" / "summaries.json").read_text())}  # fmt: skip
    assert len(summarized) >= 2  # NRT and SP observations on the raster both carry land cover
    assert {e["source_status"] for e in manifest["files"] if e["kind"] == "FIRMS_CSV"} == {
        "SUCCEEDED"}  # fmt: skip
    assert manifest["data_mode"] == "HISTORICAL_REPLAY" and "Not the frozen" in manifest["purpose"]
    assert manifest["sources"]["OPENSTREETMAP"]["license"] == "ODbL-1.0"
    assert manifest["sources"]["ESA_WORLDCOVER"]["license"] == "CC-BY-4.0"
    assert all(len(entry["sha256"]) == 64 for entry in manifest["files"])
    readme = (package / "README.txt").read_text()
    assert "Load (offline" in readme and f"--expect-sha256 {manifest['content_sha256']}" in readme
    assert verify_package(package)["ok"]
    with pytest.raises(FileExistsError):
        build_package(settings, out, "fixture-demo", ["jamnagar"], [], osm_dir)
    assert not (out / ".fixture-demo.partial").exists()

    # Tampering is refused before anything is stored.
    outside = tmp_path / "outside.csv"
    outside.write_text("latitude\n")
    for problem, change in (
        ("HASH_MISMATCH", lambda p: (p / next(e["path"] for e in manifest["files"]
                                              if e["kind"] == "FIRMS_CSV")).write_text("x")),
        ("NOT_IN_MANIFEST", lambda p: (p / "firms" / "extra.csv").write_text("x")),
        ("MISSING", lambda p: (p / "worldcover" / "summaries.json").unlink()),
        ("SYMLINK_NOT_ALLOWED", lambda p: (p / "firms" / "link.csv").symlink_to(outside)),
        ("UNSAFE_PATH", lambda p: rewrite(p, lambda files: files[0].update(path="../outside.csv"))),
        ("UNSAFE_PATH", lambda p: rewrite(p, lambda files: files[0].update(path=str(outside)))),
        ("INVALID_ENTRY", lambda p: rewrite(p, lambda files: first_firms(files).update(
            region="nowhere"))),
    ):  # fmt: skip
        copy = tmp_path / f"tampered-{problem}-{uuid4().hex[:6]}"
        shutil.copytree(package, copy)
        change(copy)
        check = verify_package(copy)
        assert not check["ok"] and problem in {p["problem"] for p in check["problems"]}
        with pytest.raises(IngestError, match="PACKAGE_VERIFICATION_FAILED"):
            load_package(target, copy)
    assert observation_ids(target) == []

    # Metadata edits with a recomputed digest pass `verify` alone but not against the hash
    # received separately.
    relabelled = tmp_path / "relabelled"
    shutil.copytree(package, relabelled)
    rewrite(relabelled, lambda files: first_firms(files).update(region="punjab"))
    assert verify_package(relabelled)["ok"]
    check = verify_package(relabelled, manifest["content_sha256"])
    assert [p["problem"] for p in check["problems"]] == ["NOT_THE_EXPECTED_PACKAGE"]
    with pytest.raises(IngestError, match="PACKAGE_VERIFICATION_FAILED"):
        load_package(target, relabelled, expect_sha256=manifest["content_sha256"])

    offline(monkeypatch)
    loaded = load_package(target, package, expect_sha256=manifest["content_sha256"])
    assert loaded["ok"] and loaded["unexpected"] == []
    assert loaded["firms"] == {"SUCCEEDED": 2} and loaded["inserted_rows"] == 4
    assert loaded["osm"] == {"jamnagar": "PARTIAL"}  # the fixture's two invalid shapes
    summaries = loaded["landcover"]["summaries"]
    assert summaries >= 1 and loaded["landcover"]["restored"] == summaries
    assert loaded["events"]["jamnagar"]["status"] == "SUCCEEDED"
    assert observation_ids(target) == observation_ids(settings)
    for observation_id in observation_ids(settings):
        assert labels(target, observation_id) == labels(settings, observation_id)

    again = load_package(target, package)
    assert again["inserted_rows"] == 0 and again["landcover"]["already_present"] == summaries
    assert observation_ids(target) == observation_ids(settings)

    # A summary the packaged chip does not reproduce is refused even with rewritten hashes.
    for field, forge in (("support", lambda row: row["support"].update(valid_fraction=0.123)),
                         ("status", lambda row: row.update(status="INSUFFICIENT")),
                         ("tile", lambda row: row.update(tile_id="N00E000"))):  # fmt: skip
        forged = tmp_path / f"forged-{field}"
        shutil.copytree(package, forged)
        rows = json.loads((forged / "worldcover" / "summaries.json").read_text())
        forge(next(row for row in rows if row["status"] == "OK"))
        payload = (json.dumps(rows, indent=1, sort_keys=True) + "\n").encode()
        (forged / "worldcover" / "summaries.json").write_bytes(payload)

        def fix(files, payload=payload):
            entry = next(e for e in files if e["path"] == "worldcover/summaries.json")
            entry["sha256"], entry["bytes"] = hashlib.sha256(payload).hexdigest(), len(payload)

        rewrite(forged, fix)
        assert verify_package(forged)["ok"]
        with pytest.raises(IngestError, match="LANDCOVER_SUMMARY_NOT_REPRODUCED"):
            restore_landcover(target, forged)


def first_firms(files):
    return next(entry for entry in files if entry["kind"] == "FIRMS_CSV")


def rewrite(package, change):
    """Edit manifest entries and recompute its digest, as someone editing a copy could."""
    manifest = json.loads((package / "manifest.json").read_text())
    change(manifest["files"])
    manifest["content_sha256"] = content_digest(manifest["files"])
    (package / "manifest.json").write_text(json.dumps(manifest))


def test_package_build_refuses_a_credential_in_a_saved_file(source, tmp_path):
    settings, osm_dir = source
    keyed = settings.model_copy(update={"firms_map_key": SecretStr("22.3")})  # in the CSV
    with pytest.raises(IngestError, match="POSSIBLE_CREDENTIAL_IN_FILE"):
        build_package(keyed, tmp_path / "packages", "keyed-demo", ["jamnagar"], [], osm_dir)
    packages = tmp_path / "packages"
    assert not packages.exists() or not any(packages.iterdir())


def test_window_exports_keep_units_provenance_and_bounds(source, monkeypatch):
    settings, _ = source
    client = TestClient(create_app(settings))
    response = client.get("/api/v1/exports/observations.csv", params=WINDOW)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["x-thermoscope-observations"] == "3"
    assert "attachment" in response.headers["content-disposition"]
    rows = list(csv.DictReader(response.text.splitlines()))
    assert len(rows) == 3 and "rule_source" not in rows[0]
    by_lat = {(r["latitude"], r["longitude"]): r for r in rows}
    missing = by_lat[("22.8", "69.6")]
    assert missing["frp_mw"] == "" and by_lat[("22.3", "69.8")]["frp_mw"] == "0.0"
    for row in rows:
        assert row["location_meaning"] == "PIXEL_CENTRE" and row["data_mode"] == MODE.value
        assert len(row["raw_file_sha256"]) == 64 and row["raw_row_number"]
        assert "FIRMS" in row["source_attribution"] and not row["source_attribution"].startswith(
            "'"
        )
        assert (row["learned_model"], row["human_validation"]) == ("NOT_SERVED", "PENDING")

    ruled = client.get("/api/v1/exports/observations.csv", params=WINDOW | {"rule_outputs": True})
    ruled_rows = list(csv.DictReader(ruled.text.splitlines()))
    assert {r["rule_source"] for r in ruled_rows} <= {
        "INDUSTRIAL", "AGRICULTURAL_BURN", "VEGETATION_FIRE", "UNKNOWN"}  # fmt: skip
    assert all(r["rules_version"] and len(r["feature_snapshot_sha256"]) == 64 for r in ruled_rows)
    assert {r["rule_basis"] for r in ruled_rows} == {"RETROSPECTIVE"}
    assert all("OpenStreetMap" in r["context_attribution"] and "WorldCover" in
               r["context_attribution"] for r in ruled_rows)  # fmt: skip
    refinery = next(r for r in ruled_rows if (r["latitude"], r["longitude"]) == ("22.3", "69.8"))
    assert refinery["context_osm_as_of_utc"].startswith("2026-01-05")  # the fixture's OSM date
    assert refinery["context_land_cover_map_year"] == "2021"
    as_operated = WINDOW | {"rule_outputs": True, "basis": "OPERATIONAL"}
    operational = client.get("/api/v1/exports/observations.csv", params=as_operated)
    assert {r["rule_basis"] for r in csv.DictReader(operational.text.splitlines())} == {
        "OPERATIONAL"}  # fmt: skip
    ruled_geo = client.get("/api/v1/exports/observations.geojson",
                           params=WINDOW | {"rule_outputs": True}).json()  # fmt: skip
    licences = {s["source"]: s["license"] for s in ruled_geo["meta"]["context_sources"]}
    assert licences == {"OpenStreetMap": "ODbL-1.0", "ESA WorldCover 2021 v200": "CC-BY-4.0"}

    geo = client.get("/api/v1/exports/observations.geojson", params=WINDOW).json()
    assert len(geo["features"]) == 3 and "context_sources" not in geo["meta"]
    assert {tuple(f["geometry"]["coordinates"]) for f in geo["features"]} == {
        (69.8, 22.3), (69.83, 22.3), (69.6, 22.8)}  # fmt: skip
    assert geo["meta"]["observations"] == 3 and "WGS84" in geo["meta"]["coordinates"]

    february = {"start_date": "2026-02-01", "end_date": "2026-02-05"}
    empty = client.get("/api/v1/exports/observations.csv", params=WINDOW | february)
    assert empty.status_code == 200 and len(empty.text.splitlines()) == 1
    none = client.get("/api/v1/exports/observations.geojson", params=WINDOW | february)
    assert none.json()["features"] == []
    fixtures = client.get("/api/v1/exports/observations.csv",
                          params=WINDOW | {"data_mode": "SYNTHETIC_FIXTURE"})  # fmt: skip
    assert len(fixtures.text.splitlines()) == 1  # modes never mix

    monkeypatch.setattr(exports, "MAX_OBSERVATIONS", 3)  # exactly at the limit: allowed
    assert client.get("/api/v1/exports/observations.geojson", params=WINDOW).status_code == 200
    monkeypatch.setattr(exports, "MAX_OBSERVATIONS", 2)
    refused = client.get("/api/v1/exports/observations.geojson", params=WINDOW)
    assert refused.status_code == 413
    body = refused.json()
    assert (body["code"], body["observations"], body["limit"]) == ("EXPORT_TOO_LARGE", 3, 2)
    monkeypatch.setattr(exports, "MAX_OBSERVATIONS", 2000)
    monkeypatch.setattr(exports, "MAX_WITH_RULES", 2)
    assert client.get("/api/v1/exports/observations.csv",
                      params=WINDOW | {"rule_outputs": True}).status_code == 413  # fmt: skip
    assert client.get("/api/v1/exports/observations.csv", params=WINDOW).status_code == 200


def test_evidence_export_separates_pixel_centre_area_and_mapped_context(source):
    settings, _ = source
    client = TestClient(create_app(settings))
    ids = {
        tuple(f["geometry"]["coordinates"]): f["id"]
        for f in client.get("/api/v1/exports/observations.geojson", params=WINDOW).json()[
            "features"
        ]
    }
    params = {"data_mode": MODE.value}
    response = client.get(f"/api/v1/exports/observations/{ids[(69.8, 22.3)]}/evidence.geojson",
                          params=params)  # fmt: skip
    assert response.status_code == 200 and "attachment" in response.headers["content-disposition"]
    evidence = response.json()
    roles = [f["properties"]["role"] for f in evidence["features"]]
    assert roles[:2] == ["PIXEL_CENTRE", "APPROXIMATE_PIXEL_AREA"]
    assert "MAPPED_CONTEXT_NOT_A_CONFIRMED_SOURCE" in roles
    assert evidence["features"][0]["geometry"] == {"type": "Point", "coordinates": [69.8, 22.3]}
    assert evidence["features"][1]["geometry"]["type"] == "Polygon"
    meta = evidence["meta"]
    assert meta["assessment"]["source"]["label"] and meta["assessment"]["rules_version"]
    assert meta["human_validation"].startswith("PENDING")
    assert meta["learned_model"].startswith("NOT_SERVED")
    licences = {s["source"]: s.get("license") for s in meta["sources"]}
    assert licences["OpenStreetMap"] == "ODbL-1.0" and licences["ESA WorldCover"] == "CC-BY-4.0"
    assert meta["history_180_days"]["days"] and all(
        d["detections"] is None for d in meta["history_180_days"]["days"] if not d["retrieved"]
    )
    far = client.get(f"/api/v1/exports/observations/{ids[(69.6, 22.8)]}/evidence.geojson",
                     params=params).json()  # fmt: skip
    assert [f["properties"]["role"] for f in far["features"]] == [
        "PIXEL_CENTRE", "APPROXIMATE_PIXEL_AREA"]  # fmt: skip
    assert far["features"][0]["properties"]["frp_mw"] is None
    unknown = client.get(f"/api/v1/exports/observations/{'f' * 64}/evidence.geojson",
                         params=params)  # fmt: skip
    assert unknown.status_code == 404
    other_mode = client.get(f"/api/v1/exports/observations/{ids[(69.8, 22.3)]}/evidence.geojson",
                            params={"data_mode": "SYNTHETIC_FIXTURE"})  # fmt: skip
    assert other_mode.status_code == 404

    review = TestClient(create_app(settings.model_copy(update={"review_only": True})))
    assert review.get(f"/api/v1/exports/observations/{ids[(69.8, 22.3)]}/evidence.geojson",
                      params=params).status_code == 403  # fmt: skip
    assert review.get("/api/v1/exports/observations.csv", params=WINDOW).status_code == 200
