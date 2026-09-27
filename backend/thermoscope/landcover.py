"""Dated land-cover summaries from ESA WorldCover 2021 v200 over the approximate pixel area.

The map year is 2021; applying it to later observations is stale context, shown as such.
Land-cover class is evidence about surroundings, not a label for the heat source.
"""

import hashlib
import json
import math
from datetime import UTC, datetime
from uuid import uuid4

import numpy as np
import rasterio
from rasterio.io import MemoryFile
from rasterio.windows import from_bounds
from sqlalchemy import text

from thermoscope.config import DataMode, Settings
from thermoscope.database import database_engine
from thermoscope.firms import IngestError
from thermoscope.object_store import ObjectStore
from thermoscope.regions import REGIONS, Bounds

PRODUCT = "ESA_WORLDCOVER_10M_2021_V200"
PRODUCT_YEAR = 2021
PUBLISHED_ON = "2022-10-28"
DOI = "10.5281/zenodo.7254221"
LICENSE = "CC-BY-4.0"
ATTRIBUTION = (
    "© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) "
    "processed by ESA WorldCover consortium"
)
ACCURACY_NOTE = "Global overall accuracy 76.7 ± 0.5 % (WorldCover 2021 v200 validation report)"
SUMMARY_VERSION = "landcover-summary-v2"
TILE_PREFIX = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/"
NODATA = 0
CLASSES = {
    10: "TREE_COVER",
    20: "SHRUBLAND",
    30: "GRASSLAND",
    40: "CROPLAND",
    50: "BUILT_UP",
    60: "BARE_SPARSE_VEGETATION",
    70: "SNOW_ICE",
    80: "PERMANENT_WATER",
    90: "HERBACEOUS_WETLAND",
    95: "MANGROVES",
    100: "MOSS_LICHEN",
}
CONTEXT_RADIUS_M = 1000.0
MIN_VALID_FRACTION = 0.5
GDAL_OPTIONS = {
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
    "GDAL_HTTP_TIMEOUT": "30",
    "GDAL_HTTP_MAX_RETRY": "2",
    "GDAL_HTTP_RETRY_DELAY": "2",
}


def tile_id(lon: float, lat: float) -> str:
    """WorldCover 3-degree tiles are named by their south-west corner."""
    south, west = math.floor(lat / 3) * 3, math.floor(lon / 3) * 3
    return f"{'N' if south >= 0 else 'S'}{abs(south):02d}{'E' if west >= 0 else 'W'}{abs(west):03d}"


def tile_url(tile: str) -> str:
    return f"{TILE_PREFIX}ESA_WorldCover_10m_2021_v200_{tile}_Map.tif"


def metres_per_degree(lat: float) -> tuple[float, float]:
    """WGS84 metres per degree of latitude and longitude at a latitude."""
    a, e2 = 6378137.0, 0.00669437999014
    phi = math.radians(lat)
    w = math.sqrt(1 - e2 * math.sin(phi) ** 2)
    return math.pi / 180 * a * (1 - e2) / w**3, math.pi / 180 * a * math.cos(phi) / w


def summarize_array(array, transform, lon, lat, radius_m: float) -> dict:
    """Class fractions over pixel centres inside a circle; nodata stays missing."""
    rows, cols = np.indices(array.shape)
    x = transform.c + (cols + 0.5) * transform.a
    y = transform.f + (rows + 0.5) * transform.e
    m_lat, m_lon = metres_per_degree(lat)
    inside = np.hypot((x - lon) * m_lon, (y - lat) * m_lat) <= radius_m
    total = int(inside.sum())
    values = array[inside]
    known = np.isin(values, list(CLASSES))
    valid = int(known.sum())
    fractions = {}
    for code, count in zip(*np.unique(values[known], return_counts=True), strict=True):
        fractions[CLASSES[int(code)]] = round(int(count) / valid, 4)
    return {
        "radius_m": round(radius_m, 1),
        "pixels": total,
        "valid_pixels": valid,
        "nodata_pixels": int((values == NODATA).sum()),
        "unrecognized_pixels": int((~known & (values != NODATA)).sum()),
        "valid_fraction": round(valid / total, 4) if total else 0.0,
        "fractions": dict(sorted(fractions.items(), key=lambda item: (-item[1], item[0]))),
    }


def read_window(source: str, lon: float, lat: float, radius_m: float):
    """Read a square window around the point; outside-tile pixels are filled as nodata."""
    if not 0 < radius_m <= 5000 or not -85 < lat < 85:
        raise IngestError("RASTER_WINDOW_OUTSIDE_PILOT_LIMITS")
    m_lat, m_lon = metres_per_degree(lat)
    dlat, dlon = radius_m / m_lat * 1.05, radius_m / m_lon * 1.05
    path = source if not source.startswith("https://") else "/vsicurl/" + source
    if source.startswith("https://") and not source.startswith(TILE_PREFIX):
        raise IngestError("ENDPOINT_NOT_ALLOWED")
    with rasterio.Env(**GDAL_OPTIONS), rasterio.open(path) as dataset:
        if (
            dataset.crs is None
            or dataset.crs.to_epsg() != 4326
            or dataset.count != 1
            or dataset.transform.b != 0
            or dataset.transform.d != 0
            or dataset.transform.a <= 0
            or dataset.transform.e >= 0
            or dataset.dtypes[0] != "uint8"
        ):
            raise IngestError("UNSUPPORTED_RASTER")
        window = from_bounds(lon - dlon, lat - dlat, lon + dlon, lat + dlat, dataset.transform)
        window = window.round_offsets().round_lengths()
        if window.width * window.height > 5_000_000:
            raise IngestError("RASTER_WINDOW_TOO_LARGE")
        array = dataset.read(1, window=window, boundless=True, fill_value=NODATA)
        transform = dataset.window_transform(window)
        b = dataset.bounds
        clipped = not (
            b.left <= lon - dlon and lon + dlon <= b.right and b.bottom <= lat - dlat
            and lat + dlat <= b.top
        )  # fmt: skip
    return array.astype(np.uint8), transform, clipped


def chip_bytes(array, transform) -> bytes:
    profile = {
        "driver": "GTiff",
        "height": array.shape[0],
        "width": array.shape[1],
        "count": 1,
        "dtype": "uint8",
        "crs": "EPSG:4326",
        "transform": transform,
        "nodata": NODATA,
        "compress": "deflate",
    }
    with MemoryFile() as memory:
        with memory.open(**profile) as chip:
            chip.write(array, 1)
        return memory.read()


def extract_landcover(
    settings: Settings,
    region_id: str,
    mode: DataMode,
    *,
    resolve=lambda tile: tile_url(tile),
    force: bool = False,
) -> dict:
    from thermoscope.context import support_radius_m  # context imports this module

    region = next((r for r in REGIONS if r["id"] == region_id), None)
    if region is None:
        raise IngestError("UNKNOWN_REGION")
    bounds = Bounds.parse(region["bbox"])
    run_id = str(uuid4())
    store = ObjectStore(settings.object_store_local_path)
    items, failed = [], []
    with database_engine(settings) as engine:
        with engine.connect() as conn:
            rows = conn.execute(
                text("""
                SELECT o.id,ST_X(o.geom),ST_Y(o.geom),
                    (o.payload->>'scan_km')::double precision,
                    (o.payload->>'track_km')::double precision
                FROM observations o
                WHERE o.geom && ST_MakeEnvelope(:west,:south,:east,:north,4326)
                  AND EXISTS (SELECT 1 FROM observation_receipts x
                      JOIN ingestion_runs r ON r.id=x.run_id WHERE x.observation_id=o.id
                      AND r.data_mode=:mode AND r.status IN ('SUCCEEDED','PARTIAL'))
                  AND (:force OR NOT EXISTS (SELECT 1 FROM landcover_summaries s
                      WHERE s.observation_id=o.id AND s.product=:product
                      AND s.summary_version=:version))
                ORDER BY o.acquired_at,o.id
            """),
                bounds.model_dump()
                | {
                    "mode": mode.value,
                    "product": PRODUCT,
                    "version": SUMMARY_VERSION,
                    "force": force,
                },
            ).all()
        for observation_id, lon, lat, scan, track in rows:
            tile = tile_id(lon, lat)
            source = resolve(tile)
            support_radius, basis = support_radius_m(scan, track)
            try:
                array, transform, clipped = read_window(
                    source, lon, lat, max(CONTEXT_RADIUS_M, support_radius)
                )
            except (IngestError, rasterio.errors.RasterioError, OSError) as error:
                code = error.code if isinstance(error, IngestError) else "RASTER_READ_FAILED"
                failed.append({"observation_id": observation_id, "error_code": code})
                continue
            support = summarize_array(array, transform, lon, lat, support_radius)
            context = summarize_array(array, transform, lon, lat, CONTEXT_RADIUS_M)
            window_sha = hashlib.sha256(
                json.dumps([array.shape, list(transform)[:6]]).encode() + array.tobytes()
            ).hexdigest()
            chip_sha = store.save_raw(chip_bytes(array, transform), suffix="tif")
            status = "OK" if support["valid_fraction"] >= MIN_VALID_FRACTION else "INSUFFICIENT"
            items.append(
                {
                    "observation_id": observation_id,
                    "tile_id": tile,
                    "source": source,
                    "window_sha256": window_sha,
                    "chip_object": f"raw/{chip_sha}.tif",
                    "tile_edge_clipped": clipped,
                    "support_basis": basis,
                    "support": support,
                    "context": context,
                    "status": status,
                }
            )
        extracted = datetime.now(UTC)
        store.save_manifest(
            run_id,
            {
                "manifest_version": 1,
                "kind": "landcover_summary",
                "run_id": run_id,
                "region_id": region_id,
                "data_mode": mode.value,
                "product": PRODUCT,
                "product_year": PRODUCT_YEAR,
                "published_on": PUBLISHED_ON,
                "doi": DOI,
                "license": LICENSE,
                "attribution": ATTRIBUTION,
                "summary_version": SUMMARY_VERSION,
                "context_radius_m": CONTEXT_RADIUS_M,
                "extracted_at": extracted.isoformat(),
                "items": [
                    {
                        k: v
                        for k, v in i.items()
                        if k
                        in {
                            "observation_id",
                            "tile_id",
                            "source",
                            "window_sha256",
                            "chip_object",
                            "tile_edge_clipped",
                            "status",
                        }
                    }
                    for i in items
                ],  # fmt: skip
                "failed": failed,
            },
        )
        with engine.begin() as conn:
            for item in items:
                conn.execute(
                    text("""
                    INSERT INTO landcover_summaries (observation_id,product,summary_version,
                        run_id,tile_id,source,window_sha256,chip_object,tile_edge_clipped,
                        support_basis,support,context,status,extracted_at)
                    VALUES (:observation_id,:product,:version,:run,:tile_id,:source,
                        :window_sha256,:chip_object,:tile_edge_clipped,:support_basis,
                        CAST(:support AS jsonb),CAST(:context AS jsonb),:status,:extracted)
                    ON CONFLICT (observation_id,product,summary_version) DO UPDATE SET
                        run_id=EXCLUDED.run_id,tile_id=EXCLUDED.tile_id,source=EXCLUDED.source,
                        window_sha256=EXCLUDED.window_sha256,chip_object=EXCLUDED.chip_object,
                        tile_edge_clipped=EXCLUDED.tile_edge_clipped,
                        support_basis=EXCLUDED.support_basis,support=EXCLUDED.support,
                        context=EXCLUDED.context,status=EXCLUDED.status,
                        extracted_at=EXCLUDED.extracted_at
                """),
                    item
                    | {
                        "product": PRODUCT,
                        "version": SUMMARY_VERSION,
                        "run": run_id,
                        "support": json.dumps(item["support"]),
                        "context": json.dumps(item["context"]),
                        "extracted": extracted,
                    },
                )
    return {
        "run_id": run_id,
        "status": "PARTIAL" if failed else "SUCCEEDED",
        "product": PRODUCT,
        "summarized": len(items),
        "failed": len(failed),
        "error_codes": sorted({f["error_code"] for f in failed}),
    }


def ranked(summary: dict) -> dict:
    """JSONB does not keep key order, so API output lists classes largest first."""
    order = sorted(summary["fractions"].items(), key=lambda item: (-item[1], item[0]))
    return summary | {"fractions": [{"class": k, "fraction": v} for k, v in order]}


def observation_landcover(conn, observation_id: str, acquired_at: datetime) -> dict | None:
    row = (
        conn.execute(
            text("""
        SELECT tile_id,window_sha256,tile_edge_clipped,support_basis,support,context,status,
            extracted_at
        FROM landcover_summaries
        WHERE observation_id=:id AND product=:product AND summary_version=:version
    """),
            {"id": observation_id, "product": PRODUCT, "version": SUMMARY_VERSION},
        )
        .mappings()
        .first()
    )
    if row is None:
        return None
    return {
        "product": PRODUCT,
        "map_year": PRODUCT_YEAR,
        "published_on": PUBLISHED_ON,
        "age_years_at_observation": acquired_at.year - PRODUCT_YEAR,
        "summary_version": SUMMARY_VERSION,
        "status": row["status"],
        "tile_id": row["tile_id"],
        "tile_edge_clipped": row["tile_edge_clipped"],
        "window_sha256": row["window_sha256"],
        "support": ranked(row["support"]),
        "context": ranked(row["context"]),
        "extracted_at": row["extracted_at"],
        "license": LICENSE,
        "doi": DOI,
        "attribution": ATTRIBUTION,
        "accuracy_note": ACCURACY_NOTE,
        "note": "Land cover from 2021 describes surroundings at that time. It is evidence, "
        "not a label for what produced the heat.",
    }
