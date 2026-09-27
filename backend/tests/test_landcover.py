import numpy as np
import pytest
import rasterio
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from rasterio.transform import from_origin
from sqlalchemy import text
from test_firms import ROW, fixture_csv, window
from thermoscope.config import DataMode, Settings
from thermoscope.database import database_engine
from thermoscope.firms import IngestError
from thermoscope.ingestion import ingest
from thermoscope.landcover import (
    CONTEXT_RADIUS_M,
    TILE_PREFIX,
    extract_landcover,
    metres_per_degree,
    read_window,
    summarize_array,
    tile_id,
    tile_url,
)

PIXEL = 0.0001  # about 10 m, like WorldCover


def synthetic_raster(path, west=69.78, north=22.32, size=400):
    """Left half cropland, right half built-up, a nodata block and one unknown code."""
    data = np.full((size, size), 40, dtype=np.uint8)
    data[:, size // 2 :] = 50
    data[260:380, 260:380] = 0  # 1.2 km nodata block centred on (69.812, 22.288)
    data[5, 5] = 7  # not a WorldCover class
    profile = {
        "driver": "GTiff",
        "height": size,
        "width": size,
        "count": 1,
        "dtype": "uint8",
        "crs": "EPSG:4326",
        "transform": from_origin(west, north, PIXEL, PIXEL),
        "nodata": 0,
    }
    with rasterio.open(path, "w", **profile) as out:
        out.write(data, 1)
    return str(path)


@pytest.mark.parametrize(
    ("lon", "lat", "expected"),
    [
        (69.8, 22.3, "N21E069"),
        (75.2762, 30.3781, "N30E075"),
        (82.7153, 24.1992, "N24E081"),
        (-0.5, -0.5, "S03W003"),
    ],
)
def test_tile_names_follow_the_south_west_corner(lon, lat, expected):
    assert tile_id(lon, lat) == expected
    assert tile_url(expected).startswith(TILE_PREFIX)


def test_wgs84_metres_per_degree_and_host_allowlist():
    m_lat, m_lon = metres_per_degree(0)
    assert m_lat == pytest.approx(110574.3, abs=0.5) and m_lon == pytest.approx(111319.5, abs=0.5)
    with pytest.raises(IngestError) as caught:
        read_window("https://example.invalid/map.tif", 69.8, 22.3, 100)
    assert caught.value.code == "ENDPOINT_NOT_ALLOWED"


def test_fractions_ignore_nodata_and_unknown_codes(tmp_path):
    path = synthetic_raster(tmp_path / "wc.tif")
    array, transform, clipped = read_window(path, 69.8, 22.3, 150)
    assert not clipped
    boundary = summarize_array(array, transform, 69.8, 22.3, 150)
    assert boundary["valid_fraction"] == 1
    assert boundary["fractions"]["CROPLAND"] == pytest.approx(0.5, abs=0.05)
    assert boundary["fractions"]["BUILT_UP"] == pytest.approx(0.5, abs=0.05)
    assert 150**2 * np.pi / 100 * 0.85 < boundary["pixels"] < 150**2 * np.pi / 100 * 1.15

    gap = summarize_array(*read_window(path, 69.812, 22.288, 700)[:2], 69.812, 22.288, 700)
    assert 0 < gap["nodata_pixels"] and gap["valid_fraction"] < 1
    assert set(gap["fractions"]) == {"BUILT_UP"} and gap["fractions"]["BUILT_UP"] == 1.0
    inside_gap = summarize_array(*read_window(path, 69.8120, 22.2880, 60)[:2], 69.8120, 22.2880, 60)
    assert inside_gap["valid_pixels"] == 0 and inside_gap["fractions"] == {}

    corner = read_window(path, 69.7806, 22.3194, 150)
    assert corner[2]  # the window runs off the raster; outside pixels are nodata, not cropland
    summary = summarize_array(corner[0], corner[1], 69.7806, 22.3194, 150)
    assert summary["unrecognized_pixels"] == 1 and summary["nodata_pixels"] > 0
    assert 0.4 < summary["valid_fraction"] < 0.75  # the off-raster part is missing, not zero


@pytest.fixture
def configured(test_database, tmp_path):
    command.upgrade(Config("alembic.ini"), "head")
    return Settings(object_store_local_path=tmp_path / "objects", firms_map_key=None)


@pytest.mark.integration
def test_extraction_is_stored_repeatable_and_shown_with_its_date(configured, tmp_path):
    raster = synthetic_raster(tmp_path / "wc.tif")
    rows = (ROW, ROW.replace("22.3,69.8", "22.288,69.812"))
    ingest(configured, window(), DataMode.SYNTHETIC_FIXTURE, payload=fixture_csv(*rows))
    report = extract_landcover(
        configured, "jamnagar", DataMode.SYNTHETIC_FIXTURE, resolve=lambda tile: raster
    )
    assert (report["status"], report["summarized"], report["failed"]) == ("SUCCEEDED", 2, 0)
    again = extract_landcover(
        configured, "jamnagar", DataMode.SYNTHETIC_FIXTURE, resolve=lambda tile: raster
    )
    assert again["summarized"] == 0  # already summarized for this product/version
    with database_engine(configured) as engine, engine.connect() as conn:
        before = dict(conn.execute(text(
            "SELECT observation_id,window_sha256 FROM landcover_summaries")).all())  # fmt: skip
    forced = extract_landcover(
        configured, "jamnagar", DataMode.SYNTHETIC_FIXTURE, resolve=lambda tile: raster,
        force=True,
    )  # fmt: skip
    with database_engine(configured) as engine, engine.connect() as conn:
        after = dict(conn.execute(text(
            "SELECT observation_id,window_sha256 FROM landcover_summaries")).all())  # fmt: skip
        statuses = (
            conn.execute(text("SELECT status FROM landcover_summaries ORDER BY status"))
            .scalars()
            .all()
        )
    assert forced["summarized"] == 2 and before == after
    assert statuses == ["INSUFFICIENT", "OK"]

    client = TestClient(create_client_app(configured))
    ids = client.get(
        "/api/v1/observations",
        params={"bbox": "69.5,22,70.5,23", "start_date": "2026-01-01", "end_date": "2026-01-03",
                "data_mode": "SYNTHETIC_FIXTURE"},
    ).json()["features"]  # fmt: skip
    by_lat = {f["geometry"]["coordinates"][1]: f["id"] for f in ids}
    body = client.get(
        f"/api/v1/observations/{by_lat[22.3]}/context", params={"data_mode": "SYNTHETIC_FIXTURE"}
    ).json()["land_cover"]
    assert body["map_year"] == 2021 and body["age_years_at_observation"] == 5
    assert body["license"] == "CC-BY-4.0" and body["attribution"].startswith("© ESA WorldCover")
    assert body["context"]["radius_m"] == CONTEXT_RADIUS_M
    ranked = body["support"]["fractions"]
    assert {x["class"] for x in ranked} == {"CROPLAND", "BUILT_UP"}
    assert ranked[0]["fraction"] >= ranked[1]["fraction"]  # largest first despite JSONB
    failing = extract_landcover(
        configured, "jamnagar", DataMode.SYNTHETIC_FIXTURE,
        resolve=lambda tile: str(tmp_path / "missing.tif"), force=True,
    )  # fmt: skip
    assert (failing["status"], failing["failed"]) == ("PARTIAL", 2)
    assert failing["error_codes"] == ["RASTER_READ_FAILED"]


def create_client_app(settings):
    from thermoscope.main import create_app

    return create_app(settings)


def test_tile_cache_slices_match_single_reads_exactly(tmp_path):
    from thermoscope.landcover import TileCache

    path = synthetic_raster(tmp_path / "wc.tif")
    points = [(69.8, 22.3), (69.812, 22.288), (69.7806, 22.3194), (69.79, 22.31)]
    cache = TileCache()
    cache.prepare(path, points, 1000)
    for lon, lat in points:
        single = read_window(path, lon, lat, 1000)
        cached = cache.read(path, lon, lat, 1000)
        assert (single[0] == cached[0]).all() and single[0].shape == cached[0].shape
        assert tuple(single[1])[:6] == tuple(cached[1])[:6] and single[2] == cached[2]


def test_tile_cache_keeps_the_pilot_limits_and_wide_support_windows(tmp_path):
    from thermoscope.landcover import TileCache

    path = synthetic_raster(tmp_path / "wide.tif", west=69.75, north=22.35, size=1000)
    points = [(69.8, 22.3), (69.81, 22.29)]
    cache = TileCache()
    cache.prepare(path, points, 2300)  # support circle wider than the 1 km context
    for lon, lat in points:
        single = read_window(path, lon, lat, 2300)
        cached = cache.read(path, lon, lat, 2300)
        assert (single[0] == cached[0]).all() and single[0].shape == cached[0].shape
    with pytest.raises(IngestError, match="RASTER_WINDOW_OUTSIDE_PILOT_LIMITS"):
        cache.read(path, 69.8, 22.3, 5001)


def test_tile_cache_rejects_unsupported_raster_layouts(tmp_path):
    from thermoscope.landcover import TileCache

    path = tmp_path / "float.tif"
    grid = from_origin(69.78, 22.32, PIXEL, PIXEL)
    profile = {"driver": "GTiff", "height": 50, "width": 50, "count": 1, "dtype": "float32",
               "crs": "EPSG:4326", "transform": grid}  # fmt: skip
    with rasterio.open(path, "w", **profile) as out:
        out.write(np.zeros((50, 50), dtype=np.float32), 1)
    with pytest.raises(IngestError, match="UNSUPPORTED_RASTER"):
        TileCache().prepare(str(path), [(69.781, 22.319), (69.782, 22.318)], 50)
