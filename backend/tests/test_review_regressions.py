"""Regression cases found by the independent P03/P04 review; all inputs are fixtures."""

from datetime import UTC, date, datetime, timedelta

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from test_assessment_db import load, night, observation_id
from test_context import import_osm
from test_firms import ROW, fixture_csv, window
from test_landcover import synthetic_raster
from test_osm import overpass
from thermoscope.assessment import Basis, Detection, history_features, source_rule
from thermoscope.config import DataMode, Settings
from thermoscope.database import database_engine
from thermoscope.ingestion import ingest
from thermoscope.landcover import extract_landcover


def test_no_history_is_not_evidence_of_non_recurrent_agriculture():
    at = datetime(2026, 4, 6, 21, tzinfo=UTC)
    current = Detection("fixture", at, 2, "N20", "D", "VIIRS_NOAA20_NRT", None)
    features = history_features([current], [], at, Basis.RETROSPECTIVE)
    context = {
        "facility_context_available": True,
        "candidates_in_support": [],
        "nearby_industrial": 0,
        "land_cover_support": {"fractions": [{"class": "CROPLAND", "fraction": 0.99}]},
    }
    result = source_rule(context, features)
    assert result["label"] == "UNKNOWN"
    assert result["reason_code"] == "INSUFFICIENT_RECURRENCE_COVERAGE"


@pytest.fixture
def configured(test_database, tmp_path):
    command.upgrade(Config("alembic.ini"), "head")
    return Settings(object_store_local_path=tmp_path, firms_map_key=None)


@pytest.mark.integration
@pytest.mark.parametrize("unusable", ["other_product", "partial_run"])
def test_unusable_runs_cannot_prove_history_was_quiet(configured, unusable):
    start = date(2026, 1, 1)
    for i in range(19):
        load(configured, start + timedelta(days=5 * i))
    with database_engine(configured) as engine, engine.begin() as conn:
        if unusable == "other_product":
            conn.execute(text("UPDATE ingestion_runs SET product='VIIRS_NOAA21_NRT'"))
        else:
            conn.execute(text("UPDATE ingestion_runs SET status='PARTIAL',rejected_rows=1"))
    current = date(2026, 4, 6)
    load(configured, current, night(current, 2), days=1)
    oid = observation_id(configured, 22.3, 69.8, current)
    body = (
        TestClient(create_app(configured))
        .get(f"/api/v1/observations/{oid}/assessment", params={"data_mode": "SYNTHETIC_FIXTURE"})
        .json()
    )
    assert body["features"]["windows"]["90"]["coverage_fraction"] == 0
    assert body["behaviour"]["label"] == "INSUFFICIENT_HISTORY"


@pytest.mark.integration
def test_point_near_extract_edge_does_not_claim_complete_facility_context(configured):
    ingest(
        configured,
        window(),
        DataMode.SYNTHETIC_FIXTURE,
        payload=fixture_csv(ROW.replace("69.8", "69.5001")),
    )
    import_osm(configured, overpass())
    with database_engine(configured) as engine, engine.connect() as conn:
        oid = conn.execute(text("SELECT id FROM observations")).scalar_one()
    body = (
        TestClient(create_app(configured))
        .get(f"/api/v1/observations/{oid}/context", params={"data_mode": "SYNTHETIC_FIXTURE"})
        .json()
    )
    assert body["association"]["status"] == "CONTEXT_NOT_COVERED"


@pytest.mark.integration
def test_landcover_window_contains_the_whole_support_circle(configured, tmp_path, monkeypatch):
    import thermoscope.landcover as landcover

    ingest(
        configured,
        window(),
        DataMode.SYNTHETIC_FIXTURE,
        payload=fixture_csv(ROW.replace(",0.4,0.5,", ",3.0,3.0,")),
    )
    path = synthetic_raster(tmp_path / "larger.tif", west=69.75, north=22.35, size=1000)
    original = landcover.read_window
    radii = []

    def inspect(source, lon, lat, radius):
        radii.append(radius)
        return original(source, lon, lat, radius)

    monkeypatch.setattr(landcover, "read_window", inspect)
    report = extract_landcover(
        configured, "jamnagar", DataMode.SYNTHETIC_FIXTURE, resolve=lambda _: path
    )
    assert report["summarized"] == 1
    assert radii[0] >= 2221


def create_app(settings):
    from thermoscope.main import create_app as factory

    return factory(settings)


def test_solar_landuse_is_not_combustion_evidence_even_when_recurrent():
    from test_assessment import RECURRENT, context, feature
    from thermoscope.context import power_context

    tags = {
        "power": "plant",
        "plant:source": "solar",
        "plant:method": "photovoltaic",
        "landuse": "industrial",
    }
    power_source, thermal = power_context(tags)
    assert power_source == "solar" and not thermal
    candidate = feature("power=plant", "POWER") | {
        "power_source": power_source,
        "thermal_source_candidate": thermal,
    }
    result = source_rule(context([candidate], {"BUILT_UP": 0.6}), RECURRENT)
    assert result["label"] == "UNKNOWN"
    assert result["reason_code"] == "NON_THERMAL_POWER_CONTEXT"
    assert power_context({"power": "plant", "plant:source": "coal"}) == ("coal", True)
