"""Facility context against a real disposable PostGIS database; fixtures are labelled as such."""

import hashlib
import math

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from test_firms import ROW, fixture_csv, window
from test_osm import overpass, square, way
from thermoscope.config import DataMode, Settings
from thermoscope.context_ingestion import ingest_osm
from thermoscope.database import database_engine
from thermoscope.firms import IngestError
from thermoscope.ingestion import ingest
from thermoscope.main import create_app

pytestmark = pytest.mark.integration

A = ROW  # 69.8, 22.3: inside the refinery, next to a flare
B = ROW.replace("22.3,69.8", "22.303,69.8")  # inside a hole cut out of the refinery
C = ROW.replace("22.3,69.8", "22.3,69.83")  # only a mapped industrial area 1.2 km away
D = ROW.replace("22.3,69.8", "22.8,69.6")  # nothing mapped nearby


def metres_per_degree_longitude(latitude: float) -> float:
    a, e2 = 6378137.0, 0.00669437999014
    phi = math.radians(latitude)
    return math.pi / 180 * a * math.cos(phi) / math.sqrt(1 - e2 * math.sin(phi) ** 2)


def fixture_osm(base="2026-01-05T00:00:00Z"):
    refinery = {
        "type": "relation",
        "id": 7,
        "version": 2,
        "timestamp": base,
        "tags": {"type": "multipolygon", "industrial": "refinery", "name": "Fixture refinery"},
        "members": [
            {"type": "way", "ref": 1, "role": "outer", "geometry": square(69.795, 22.295, 0.01)},
            {"type": "way", "ref": 2, "role": "inner", "geometry": square(69.799, 22.302, 0.002)},
        ],
    }
    bowtie = [(69.9, 22.9), (69.91, 22.91), (69.91, 22.9), (69.9, 22.91), (69.9, 22.9)]
    flat = [(69.95, 22.95), (69.96, 22.95), (69.97, 22.95), (69.95, 22.95)]
    return overpass(
        {"type": "node", "id": 5, "lat": 22.3, "lon": 69.801, "tags": {"man_made": "flare"}},
        refinery,
        way(20, square(69.842, 22.295, 0.005), landuse="industrial"),
        way(21, [{"lon": x, "lat": y} for x, y in bowtie], landuse="industrial"),
        way(22, [{"lon": x, "lat": y} for x, y in flat], landuse="industrial"),
        base=base,
    )


@pytest.fixture
def configured(test_database, tmp_path):
    command.upgrade(Config("alembic.ini"), "head")
    return Settings(object_store_local_path=tmp_path, firms_map_key=None)


def import_osm(settings, payload, **extra):
    digest = hashlib.sha256(payload).hexdigest()
    return ingest_osm(
        settings, "jamnagar", payload=payload, expected_sha256=digest, provider="TEST_FIXTURE",
        **extra,
    )  # fmt: skip


def context(client, observation_id, mode="SYNTHETIC_FIXTURE"):
    return client.get(f"/api/v1/observations/{observation_id}/context", params={"data_mode": mode})


def ids_by_latitude_longitude(settings):
    with database_engine(settings) as engine, engine.connect() as conn:
        rows = conn.execute(
            text("""
            SELECT o.id,ST_X(o.geom),ST_Y(o.geom),r.data_mode FROM observations o
            JOIN observation_receipts x ON x.observation_id=o.id
            JOIN ingestion_runs r ON r.id=x.run_id
        """)
        ).all()
    return {(round(lon, 3), round(lat, 3), mode): oid for oid, lon, lat, mode in rows}


def test_context_association_distances_ambiguity_and_fixture_isolation(configured):
    payload = fixture_csv(A, B, C, D)
    assert (
        ingest(configured, window(), DataMode.SYNTHETIC_FIXTURE, payload=payload)["inserted_rows"]
        == 4
    )
    # The same bytes imported as replay create separate real-namespace observations.
    assert (
        ingest(configured, window(), DataMode.HISTORICAL_REPLAY, payload=payload)["inserted_rows"]
        == 4
    )
    ids = ids_by_latitude_longitude(configured)
    client = TestClient(create_app(configured))

    before = context(client, ids[(69.8, 22.3, "SYNTHETIC_FIXTURE")]).json()
    assert before["association"]["status"] == "CONTEXT_NOT_COVERED"
    assert before["facility_snapshot"] is None and before["context_timing"] is None
    assert before["support_region"]["geometry"]["type"] == "Polygon"

    first = import_osm(configured, fixture_osm())
    again = import_osm(configured, fixture_osm())
    assert first["status"] == again["status"] == "PARTIAL"
    assert (first["accepted_elements"], first["rejected_elements"]) == (4, 1)
    assert first["snapshot_id"] == again["snapshot_id"]
    with database_engine(configured) as engine, engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM facilities")).scalar_one() == 4
        assert conn.execute(
            text("SELECT reason FROM context_quarantine WHERE osm_id=22")
        ).scalars().all() == ["INVALID_GEOMETRY", "INVALID_GEOMETRY"]
        assert conn.execute(
            text("SELECT ST_IsValid(geom) AND GeometryType(geom) LIKE '%POLYGON' "
                 "FROM facilities WHERE osm_id=21")
        ).scalar_one()  # fmt: skip

    lon_metres = metres_per_degree_longitude(22.3)
    a = context(client, ids[(69.8, 22.3, "SYNTHETIC_FIXTURE")]).json()
    assert a["association"]["status"] == "MULTIPLE_MAPPED_FEATURES"
    assert a["association"]["facility_types_in_support"] == ["REFINERY", "UNKNOWN"]
    assert a["context_timing"] == "RETROSPECTIVE"
    assert a["facility_snapshot"]["license"] == "ODbL-1.0"
    refinery, flare = a["association"]["candidates"][:2]
    assert (refinery["osm_type"], refinery["distance_m"], refinery["contains_pixel_centre"]) == (
        "relation",
        0,
        True,
    )
    assert 0.5 < refinery["support_overlap_fraction"] < 1  # the hole removes part of the circle
    assert flare["osm_type"] == "node" and flare["support_overlap_fraction"] is None
    assert flare["distance_m"] == pytest.approx(0.001 * lon_metres, abs=0.5)

    b = context(client, ids[(69.8, 22.303, "SYNTHETIC_FIXTURE")]).json()
    hole = next(c for c in b["association"]["candidates"] if c["osm_type"] == "relation")
    assert not hole["contains_pixel_centre"]
    assert hole["distance_m"] == pytest.approx(0.001 * metres_per_degree_longitude(22.303), abs=0.5)

    c = context(client, ids[(69.83, 22.3, "SYNTHETIC_FIXTURE")]).json()
    assert c["association"]["status"] == "NEARBY_ONLY"
    assert c["association"]["candidates"][0]["distance_m"] == pytest.approx(
        0.012 * lon_metres, abs=1
    )
    d = context(client, ids[(69.6, 22.8, "SYNTHETIC_FIXTURE")]).json()
    assert d["association"]["status"] == "NO_MAPPED_FEATURE_NEARBY"

    # Real observations at the same coordinates never borrow fixture facilities.
    real = context(client, ids[(69.8, 22.3, "HISTORICAL_REPLAY")], "HISTORICAL_REPLAY").json()
    assert real["association"]["status"] == "CONTEXT_NOT_COVERED"
    assert context(client, ids[(69.8, 22.3, "SYNTHETIC_FIXTURE")], "LIVE").status_code == 404
    assert context(client, "f" * 64).status_code == 404
    assert context(client, "not-a-hash").status_code == 422

    layer = client.get(
        "/api/v1/map/facilities.geojson",
        params={"bbox": "69.5,22,70.5,23", "data_mode": "SYNTHETIC_FIXTURE"},
    ).json()
    assert len(layer["features"]) == 4 and not layer["meta"]["truncated"]
    assert layer["meta"]["snapshots"][0]["attribution"].startswith("© OpenStreetMap")
    assert (
        client.get(
            "/api/v1/map/facilities.geojson",
            params={"bbox": "69.5,22,70.5,23", "data_mode": "HISTORICAL_REPLAY"},
        ).json()["features"]
        == []
    )
    assert (
        client.get("/api/v1/map/facilities.geojson", params={"bbox": "0,0,90,90"}).status_code
        == 422
    )


def test_prior_state_timing_hash_mismatch_and_provider_failure_keep_data(configured):
    ingest(configured, window(), DataMode.SYNTHETIC_FIXTURE, payload=fixture_csv(A))
    older = fixture_osm(base="2025-12-01T00:00:00Z")
    assert import_osm(configured, older)["status"] == "PARTIAL"
    client = TestClient(create_app(configured))
    observation = next(iter(ids_by_latitude_longitude(configured).values()))
    assert context(client, observation).json()["context_timing"] == "PRIOR_STATE"

    wrong = ingest_osm(
        configured, "jamnagar", payload=older, expected_sha256="0" * 64, provider="TEST_FIXTURE"
    )
    assert (wrong["status"], wrong["error_code"]) == ("FAILED", "FILE_HASH_MISMATCH")

    def outage(query):
        raise IngestError("PROVIDER_UNAVAILABLE")

    failed = ingest_osm(configured, "jamnagar", fetcher=outage, provider="TEST_FIXTURE")
    assert (failed["status"], failed["error_code"]) == ("FAILED", "PROVIDER_UNAVAILABLE")
    with database_engine(configured) as engine, engine.connect() as conn:
        statuses = conn.execute(
            text("SELECT status,count(*) FROM context_runs GROUP BY status ORDER BY status")
        ).all()
        assert [tuple(row) for row in statuses] == [("FAILED", 2), ("PARTIAL", 1)]
        assert conn.execute(text("SELECT count(*) FROM facilities")).scalar_one() == 4
    assert context(client, observation).json()["association"]["status"] == (
        "MULTIPLE_MAPPED_FEATURES"
    )
    with pytest.raises(IngestError):
        ingest_osm(configured, "atlantis", payload=older, expected_sha256="0" * 64)
