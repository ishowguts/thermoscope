"""NOAA-20 SP/NRT history continuity without letting other products, partial runs or duplicate
SP/NRT detections inflate evidence (P05 reconciliation); all inputs are fixtures."""

from datetime import UTC, date, datetime, timedelta

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from test_assessment_db import load, night, observation_id
from test_firms import HEADER
from thermoscope.assessment import Detection, product_family, reconcile_stream
from thermoscope.config import DataMode, Settings
from thermoscope.database import database_engine
from thermoscope.ingestion import ingest
from thermoscope.main import create_app
from thermoscope.regions import Bounds, Window

NRT, SP = "VIIRS_NOAA20_NRT", "VIIRS_NOAA20_SP"


def detection(day: date, product: str, satellite="N20"):
    return Detection(f"{product}-{day}", datetime(day.year, day.month, day.day, 21, tzinfo=UTC),
                     2.0, satellite, "N", product, None)  # fmt: skip


def test_product_family_joins_only_noaa20_nrt_and_sp():
    assert set(product_family(NRT)) == set(product_family(SP)) == {NRT, SP}
    assert product_family("VIIRS_NOAA21_NRT") == ("VIIRS_NOAA21_NRT",)


def test_sp_supersedes_nrt_on_days_it_covers():
    d1, d2, d3 = date(2026, 6, 29), date(2026, 6, 30), date(2026, 7, 1)
    runs = [(d1, d2, None, SP), (d2, d3, None, NRT)]
    detections = [detection(d2, SP), detection(d2, NRT), detection(d3, NRT)]
    kept, coverage, dropped = reconcile_stream(detections, runs)
    assert dropped == 1 and [d.product for d in kept] == [SP, NRT]
    assert len(coverage) == 2
    # Without a qualifying SP run, only the NRT copy of the same overpass is dropped.
    morning = Detection("nrt-am", datetime(2026, 7, 1, 9, tzinfo=UTC), 1.0, "N20", "D", NRT, None)
    kept, _, dropped = reconcile_stream([detection(d3, SP), detection(d3, NRT), morning], [])
    assert dropped == 1 and [d.id for d in kept] == [f"{SP}-{d3}", "nrt-am"]
    # An operational replay cannot use SP data that arrived after as_of.
    as_of = datetime(2026, 7, 2, tzinfo=UTC)
    late = [(d3, d3, datetime(2026, 9, 1, tzinfo=UTC), SP)]
    live_nrt = Detection("nrt", datetime(2026, 7, 1, 21, tzinfo=UTC), 2.0, "N20", "N", NRT,
                         datetime(2026, 7, 1, 23, tzinfo=UTC))  # fmt: skip
    kept, _, dropped = reconcile_stream([live_nrt], late, as_of, "OPERATIONAL")
    assert dropped == 0 and kept == [live_nrt]
    kept, _, dropped = reconcile_stream([live_nrt], late, as_of, "RETROSPECTIVE")
    assert dropped == 1


@pytest.fixture
def configured(test_database, tmp_path):
    command.upgrade(Config("alembic.ini"), "head")
    return Settings(object_store_local_path=tmp_path, firms_map_key=None)


def sp_load(settings, start: date, *rows, days=5):
    window = Window(product=SP, bounds=Bounds.parse("69.5,22,70.5,23"), start_date=start,
                    days=days)  # fmt: skip
    header = HEADER.rstrip("\n") + ",type\n"
    body = header + "".join(r.rstrip("\n").replace("2.0NRT", "2") + ",0\n" for r in rows)
    report = ingest(settings, window, DataMode.SYNTHETIC_FIXTURE, payload=body.encode())
    assert report["status"] == "SUCCEEDED", report
    return report


@pytest.mark.integration
def test_nrt_assessment_uses_sp_history_once_and_ignores_other_products(configured):
    start = date(2026, 1, 1)
    for i in range(18):  # SP archive 1 Jan – 31 Mar, one night detection per window
        sp_load(
            configured, start + timedelta(days=5 * i), night(start + timedelta(days=5 * i + 2), 2)
        )
    # The last SP day (31 March) is also fetched as NRT; the same detection arrives twice.
    duplicate = date(2026, 3, 29)
    load(configured, duplicate, night(duplicate, 2), days=3)
    current = date(2026, 4, 6)
    load(configured, date(2026, 4, 1))
    load(configured, date(2026, 4, 6), night(current, 2.1), days=1)
    client = TestClient(create_app(configured))
    oid = observation_id(configured, 22.3, 69.8, current)
    params = {"data_mode": "SYNTHETIC_FIXTURE"}
    body = client.get(f"/api/v1/observations/{oid}/assessment", params=params).json()
    window90 = body["features"]["windows"]["90"]
    assert window90["coverage_fraction"] == 1.0  # SP days count as retrieved NOAA-20 days
    # 17 SP detections fall in the window; the NRT copy of 29 March is not counted again.
    assert window90["detections"] == window90["active_days"] == 17
    assert body["stream"] == {"products": [NRT, SP], "nrt_superseded_by_sp": 1}

    # A different satellite's detection at the same place never adds history.
    with database_engine(configured) as engine, engine.begin() as conn:
        conn.execute(text("UPDATE ingestion_runs SET product='VIIRS_NOAA21_NRT' "
                          "WHERE start_date=:d"), {"d": duplicate})  # fmt: skip
        conn.execute(
            text("""UPDATE observations SET product='VIIRS_NOAA21_NRT'
            WHERE product=:nrt AND acquired_at::date=:d"""),
            {"nrt": NRT, "d": duplicate},
        )
    again = client.get(f"/api/v1/observations/{oid}/assessment", params=params).json()
    assert again["features"]["windows"]["90"]["detections"] == 17
    assert again["stream"]["nrt_superseded_by_sp"] == 0
