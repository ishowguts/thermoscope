"""Event/site runs against a real disposable PostGIS database, using labelled fixtures."""

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from test_firms import ROW, fixture_csv
from thermoscope.config import DataMode, Settings
from thermoscope.database import database_engine
from thermoscope.events import build_event_run
from thermoscope.ingestion import ingest
from thermoscope.main import create_app
from thermoscope.regions import Bounds, Window

pytestmark = pytest.mark.integration


def row(lat, lon, day, hhmm, frp):
    return (
        ROW.replace("22.3,69.8", f"{lat},{lon}")
        .replace("2026-01-02,905", f"2026-01-{day:02d},{hhmm}")
        .replace(",295,0,D", f",295,{frp},D")
    )


P1 = row(22.3, 69.8, 2, "0905", 1.5)
P2 = row(22.3, 69.801, 2, "2100", 4.0)  # 103 m away, same event
P3 = row(22.3, 69.83, 2, "2100", 2.0)  # 3 km away: separate event and site
LATE = row(22.3, 69.8005, 1, "2100", 0.5)  # earlier acquisition that arrives later


@pytest.fixture
def configured(test_database, tmp_path):
    command.upgrade(Config("alembic.ini"), "head")
    return Settings(object_store_local_path=tmp_path, firms_map_key=None)


def fixture_window():
    return Window(bounds=Bounds.parse("69.5,22,70.5,23"), start_date="2026-01-01", days=3)


def load(settings, *rows):
    return ingest(
        settings, fixture_window(), DataMode.SYNTHETIC_FIXTURE, payload=fixture_csv(*rows)
    )


def memberships(settings, run_id):
    with database_engine(settings) as engine, engine.connect() as conn:
        rows = conn.execute(
            text("SELECT event_id,observation_id FROM event_observations WHERE run_id=:r"),
            {"r": run_id},
        ).all()
    return sorted((e, o) for e, o in rows)


def test_deterministic_runs_late_arrival_lineage_and_api(configured):
    load(configured, P1, P2, P3)
    first = build_event_run(configured, "jamnagar", DataMode.SYNTHETIC_FIXTURE)
    assert (first["event_count"], first["site_count"], first["input_count"]) == (2, 2, 3)
    unchanged = build_event_run(configured, "jamnagar", DataMode.SYNTHETIC_FIXTURE)
    assert unchanged == {"status": "UNCHANGED", "run_id": first["run_id"]}
    forced = build_event_run(configured, "jamnagar", DataMode.SYNTHETIC_FIXTURE, force=True)
    assert forced["run_id"] != first["run_id"]
    assert memberships(configured, forced["run_id"]) == memberships(configured, first["run_id"])
    assert forced["lineage"] == {"SAME": 2}
    # Real-mode runs never see fixture observations.
    assert build_event_run(configured, "jamnagar", DataMode.HISTORICAL_REPLAY)["event_count"] == 0

    load(configured, LATE)
    late = build_event_run(configured, "jamnagar", DataMode.SYNTHETIC_FIXTURE)
    assert (late["late_arrivals"], late["event_count"], late["lineage"]) == (
        1,
        2,
        {"GREW": 1, "SAME": 1},
    )

    client = TestClient(create_app(configured))
    params = {
        "bbox": "69.5,22,70.5,23",
        "start_date": "2026-01-01",
        "end_date": "2026-01-03",
        "data_mode": "SYNTHETIC_FIXTURE",
    }
    listing = client.get("/api/v1/events", params=params).json()
    assert len(listing["features"]) == 2
    assert listing["meta"]["runs"][0]["id"] == late["run_id"]
    grown = next(f for f in listing["features"] if f["properties"]["observation_count"] == 3)
    assert grown["properties"]["overpass_count"] == 3
    assert grown["properties"]["max_frp_mw"] == 4.0  # the maximum, never a sum
    assert 100 < grown["properties"]["diameter_m"] < 110
    detail = client.get(f"/api/v1/events/{grown['id']}", params={"data_mode": "SYNTHETIC_FIXTURE"})
    body = detail.json()["properties"]
    assert [o["frp_mw"] for o in body["observations"]] == [0.5, 1.5, 4.0]
    assert [link["relation"] for link in body["lineage"]] == ["GREW"]
    assert body["lineage"][0]["previous_run_id"] == forced["run_id"]

    observation = body["observations"][0]["id"]
    context = client.get(
        f"/api/v1/observations/{observation}/context", params={"data_mode": "SYNTHETIC_FIXTURE"}
    ).json()
    assert context["event"]["event_id"] == grown["id"]
    assert context["event"]["site"]["event_count"] == 1
    assert (
        client.get(
            f"/api/v1/events/{grown['id']}", params={"data_mode": "HISTORICAL_REPLAY"}
        ).status_code
        == 404
    )
    assert client.get("/api/v1/events", params=params | {"bbox": "0,0,9,9"}).status_code == 422
