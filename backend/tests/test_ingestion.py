import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from test_firms import ROW, fixture_csv, window
from thermoscope.config import DataMode, Settings
from thermoscope.database import database_engine
from thermoscope.firms import IngestError
from thermoscope.ingestion import ingest
from thermoscope.main import create_app

pytestmark = pytest.mark.integration


@pytest.fixture
def configured(test_database, tmp_path):
    command.upgrade(Config("alembic.ini"), "head")
    return Settings(object_store_local_path=tmp_path, firms_map_key=None)


def query(mode="SYNTHETIC_FIXTURE", **extra):
    return {
        "bbox": "69.5,22,70.5,23",
        "start_date": "2026-01-01",
        "end_date": "2026-01-03",
        "data_mode": mode,
        **extra,
    }


def test_reimport_provenance_modes_quarantine_and_pagination(configured):
    payload = fixture_csv(ROW, ROW.replace("22.3", "22.4"), ROW.replace("22.3", "92"))
    first = ingest(configured, window(), DataMode.SYNTHETIC_FIXTURE, payload=payload)
    second = ingest(configured, window(), DataMode.SYNTHETIC_FIXTURE, payload=payload)
    assert first["status"] == second["status"] == "PARTIAL"
    assert (first["total_rows"], first["inserted_rows"], first["rejected_rows"]) == (3, 2, 1)
    assert second["inserted_rows"] == 0 and second["duplicate_rows"] == 2
    assert first["snapshot_id"] == second["snapshot_id"]
    manifest = json.loads(
        (configured.object_store_local_path / "manifests" / (first["run_id"] + ".json")).read_text()
    )
    assert (configured.object_store_local_path / manifest["raw_object"]).read_bytes() == payload
    client = TestClient(create_app(configured))
    page = client.get("/api/v1/observations", params=query(limit=1)).json()
    assert page["meta"]["total_observations"] == 2 and page["meta"]["next_offset"] == 1
    feature = page["features"][0]
    assert feature["geometry"]["coordinates"][0] == 69.8
    assert feature["properties"]["source_confidence"] == "n"
    assert feature["properties"]["first_available_at"] is None
    assert feature["properties"]["raw_sha256"] == first["content_sha256"]
    assert (
        feature["id"]
        != client.get("/api/v1/observations", params=query(limit=1, offset=1)).json()["features"][
            0
        ]["id"]
    )
    assert (
        client.get("/api/v1/observations", params=query("HISTORICAL_REPLAY")).json()["features"]
        == []
    )
    assert (
        client.get("/api/v1/catalog", params={"data_mode": "SYNTHETIC_FIXTURE"}).json()["regions"][
            0
        ]["total_stored"]
        == 2
    )
    for invalid in [
        query(bbox="-180,-90,180,90"),
        query(limit=501),
        query(end_date="2026-03-01"),
        query(offset=-1),
        query(bbox="69,22,nan,23"),
        query(start_date="9999-12-31", end_date="9999-12-31"),
    ]:
        assert client.get("/api/v1/observations", params=invalid).status_code == 422


def test_concurrent_overlapping_snapshots_have_one_observation_each(configured):
    payload = fixture_csv(ROW, ROW.replace("22.3", "22.4"))

    def run(content):
        return ingest(configured, window(), DataMode.SYNTHETIC_FIXTURE, payload=content)

    with ThreadPoolExecutor(max_workers=2) as pool:
        reports = list(pool.map(run, [payload, fixture_csv(ROW.replace("22.3", "22.4"), ROW)]))
    assert all(r["status"] == "SUCCEEDED" for r in reports)
    assert sum(r["inserted_rows"] for r in reports) == 2
    with database_engine(configured) as engine, engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM observations")).scalar_one() == 2
        assert conn.execute(text("SELECT count(*) FROM observation_receipts")).scalar_one() == 4


def test_replay_and_fetch_share_identity_and_provider_failure_preserves_data(configured):
    replay = ingest(configured, window(), DataMode.HISTORICAL_REPLAY, payload=fixture_csv())
    live = ingest(configured, window(), DataMode.LIVE, fetcher=lambda *_: fixture_csv())
    assert replay["inserted_rows"] == 1 and live["inserted_rows"] == 0
    client = TestClient(create_app(configured))
    first_available = client.get("/api/v1/observations", params=query("LIVE")).json()["features"][
        0
    ]["properties"]["first_available_at"]
    ingest(configured, window(), DataMode.LIVE, fetcher=lambda *_: fixture_csv())

    def failed(*_):
        raise IngestError("PROVIDER_UNAVAILABLE")

    report = ingest(configured, window(), DataMode.LIVE, fetcher=failed)
    assert report["status"] == "FAILED" and report["error_code"] == "PROVIDER_UNAVAILABLE"
    page = (
        TestClient(create_app(configured)).get("/api/v1/observations", params=query("LIVE")).json()
    )
    assert page["meta"]["total_observations"] == 1
    assert page["meta"]["latest_run"]["status"] == "FAILED"
    assert page["features"][0]["properties"]["availability_basis"] == "OBSERVED_AT_FETCH"
    assert page["features"][0]["properties"]["source_published_at"] is None
    assert page["features"][0]["properties"]["first_available_at"] == first_available


def test_changed_source_payload_is_preserved_for_review_without_overwriting(configured):
    ingest(configured, window(), DataMode.SYNTHETIC_FIXTURE, payload=fixture_csv())
    changed = ingest(
        configured,
        window(),
        DataMode.SYNTHETIC_FIXTURE,
        payload=fixture_csv(ROW.replace(",0,D", ",6,D")),
    )
    assert changed["status"] == "PARTIAL" and changed["rejected_rows"] == 1
    assert changed["total_rows"] == 1 and changed["accepted_rows"] == 0
    with database_engine(configured) as engine, engine.connect() as conn:
        assert (
            conn.execute(text("SELECT payload->>'frp_mw' FROM observations")).scalar_one() == "0.0"
        )
        assert (
            conn.execute(text("SELECT reason FROM quarantined_rows")).scalar_one()
            == "SOURCE_REVISION_CONFLICT"
        )


def test_file_cannot_be_live_and_wrong_hash_cannot_import(configured):
    with pytest.raises(IngestError, match="FILE_IMPORT_CANNOT_BE_LIVE"):
        ingest(configured, window(), DataMode.LIVE, payload=fixture_csv())
    report = ingest(
        configured,
        window(),
        DataMode.HISTORICAL_REPLAY,
        payload=fixture_csv(),
        expected_sha256="0" * 64,
    )
    assert report["status"] == "FAILED" and report["error_code"] == "FILE_HASH_MISMATCH"
