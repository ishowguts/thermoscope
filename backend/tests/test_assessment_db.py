"""P04 assessment and timeline against a real disposable PostGIS database (labelled fixtures)."""

from datetime import date, timedelta

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from test_events_db import row
from test_firms import fixture_csv
from thermoscope.config import DataMode, Settings
from thermoscope.database import database_engine
from thermoscope.ingestion import ingest
from thermoscope.main import create_app
from thermoscope.regions import Bounds, Window

pytestmark = pytest.mark.integration


def night(day: date, frp: float, lat=22.3, lon=69.8, hhmm="2100"):
    line = row(lat, lon, day.day, hhmm, frp).replace("2026-01-", f"{day:%Y-%m}-")
    return line.replace(",D\n", ",N\n")


@pytest.fixture
def configured(test_database, tmp_path):
    command.upgrade(Config("alembic.ini"), "head")
    return Settings(object_store_local_path=tmp_path, firms_map_key=None)


def load(settings, start: date, *rows, days=5):
    window = Window(bounds=Bounds.parse("69.5,22,70.5,23"), start_date=start, days=days)
    body = fixture_csv(*rows) if rows else fixture_csv().splitlines(keepends=True)[0]
    report = ingest(settings, window, DataMode.SYNTHETIC_FIXTURE, payload=body)
    assert report["status"] == "SUCCEEDED", report
    return report


def observation_id(settings, lat, lon, day):
    with database_engine(settings) as engine, engine.connect() as conn:
        return conn.execute(
            text("""SELECT id FROM observations WHERE ST_Y(geom)=:lat AND ST_X(geom)=:lon
                    AND acquired_at::date=:day"""),
            {"lat": lat, "lon": lon, "day": day},
        ).scalar_one()


def test_history_rules_availability_and_timeline(configured):
    start = date(2026, 1, 1)
    values = [1.8, 2.0, 2.2, 1.9, 2.1, 2.4, 1.7, 2.0, 2.3, 1.9, 2.0, 2.2, 1.8, 2.1, 2.0, 1.9, 2.2,
              2.0, 1.95]  # fmt: skip
    for i, value in enumerate(values):  # 19 windows of 5 days, one night detection each
        day = start + timedelta(days=5 * i + 2)
        load(configured, start + timedelta(days=5 * i), night(day, value))
    current_day, spike_day, later_day = date(2026, 4, 6), date(2026, 4, 7), date(2026, 4, 10)
    load(configured, current_day, night(current_day, 2.05), night(spike_day, 40.0),
         night(spike_day, 3.0, lat=22.5, lon=69.9), night(later_day, 99.0), days=5)  # fmt: skip

    client = TestClient(create_app(configured))
    fixture = {"data_mode": "SYNTHETIC_FIXTURE"}

    def get(obs, suffix="assessment", **params):
        return client.get(f"/api/v1/observations/{obs}/{suffix}", params=fixture | params)

    normal = get(observation_id(configured, 22.3, 69.8, current_day)).json()
    assert normal["behaviour"]["label"] == "RECURRENT_WITHIN_BASELINE"
    assert normal["features"]["windows"]["90"]["coverage_fraction"] >= 0.8
    assert normal["features"]["windows"]["90"]["active_days"] == 18
    assert normal["features"]["excluded_after_as_of"] == 2  # the 40 MW spike and the 99 MW day
    assert normal["source"]["label"] == "UNKNOWN"  # fixture mode has no facility snapshot
    assert normal["priority"]["label"] == "MEDIUM"

    spike_id = observation_id(configured, 22.3, 69.8, spike_day)
    spike = get(spike_id).json()
    assert spike["behaviour"]["label"] == "ABNORMAL_RELATIVE_TO_BASELINE"
    assert spike["behaviour"]["direction"] == "HIGHER"
    assert spike["priority"]["label"] == "REVIEW"
    assert spike["features"]["excluded_after_as_of"] == 1  # only the later 99 MW detection

    quiet = get(observation_id(configured, 22.5, 69.9, spike_day)).json()
    assert quiet["behaviour"]["label"] == "NEW_OR_TRANSIENT"

    operational = get(spike_id, basis="OPERATIONAL").json()
    assert operational["behaviour"]["label"] == "INSUFFICIENT_HISTORY"
    assert operational["features"]["excluded_unknown_availability"] >= 19
    assert operational["source"]["reason_code"] == "CONTEXT_UNAVAILABLE_AS_OF"

    later = get(spike_id, as_of="2026-04-12T00:00:00Z").json()
    assert later["features"]["excluded_after_as_of"] == 0
    assert later["features"]["current"]["detections"] == 0  # nothing in the last 24 h
    assert get(spike_id, as_of="2026-04-01T00:00:00Z").status_code == 422  # before observation
    assert get(spike_id, as_of="2026-04-12T00:00:00").status_code == 422  # no timezone
    assert get(spike_id, as_of="2999-01-01T00:00:00Z").status_code == 422  # future
    assert get(spike_id, basis="GUESS").status_code == 422
    assert get("0" * 64).status_code == 404
    assert (
        client.get(
            f"/api/v1/observations/{spike_id}/assessment", params={"data_mode": "HISTORICAL_REPLAY"}
        ).status_code
        == 404
    )

    timeline = get(spike_id, "timeline", days=100).json()
    assert len(timeline["days"]) == 101 and timeline["days"][-1]["date"] == str(spike_day)
    by_day = {d["date"]: d for d in timeline["days"]}
    assert by_day[str(spike_day)]["max_frp_mw"] == 40.0
    assert str(later_day) not in by_day  # nothing after as_of
    assert by_day["2026-01-03"]["retrieved"] and by_day["2026-01-03"]["detections"] == 1
    assert not by_day["2025-12-31"]["retrieved"]  # never fetched: unknown, not zero
    assert get(spike_id, "timeline", days=500).status_code == 422
