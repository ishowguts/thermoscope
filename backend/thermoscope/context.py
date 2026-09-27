"""Approximate pixel support and mapped-facility association for one observation.

The support region is a circle, not the sensor footprint: pixel orientation is unknown here.
Every mapped feature intersecting it is kept as a candidate with its distance and overlap.
Nearest is not responsible, and "no mapped feature" is not evidence that no industry exists.
"""

import json
import math
from datetime import UTC, datetime

from sqlalchemy import text

from thermoscope.config import DataMode, Settings
from thermoscope.database import database_engine
from thermoscope.events import observation_event
from thermoscope.landcover import observation_landcover
from thermoscope.osm import PROVIDER
from thermoscope.regions import Bounds

SUPPORT_VERSION = "support-v1"
ASSOCIATION_VERSION = "facility-association-v1"
NOMINAL_VIIRS_I_KM = 0.375
# Engineering default for geolocation error, not a measured accuracy of this product.
GEOLOCATION_BUFFER_M = 100.0
CONTEXT_RADIUS_M = 2000.0
MAX_CANDIDATES = 50
MAX_MAP_FEATURES = 2000

MISSINGNESS_NOTE = (
    "OpenStreetMap is volunteer-mapped and incomplete. A missing feature is not evidence that "
    "no industry exists, and a mapped feature is not proof of the heat source."
)


def support_radius_m(scan_km: float | None, track_km: float | None) -> tuple[float, str]:
    """Half the pixel diagonal covers the pixel in any orientation, plus a location buffer."""
    basis = "SCAN_TRACK"
    if not scan_km or not track_km or scan_km <= 0 or track_km <= 0:
        scan_km = track_km = NOMINAL_VIIRS_I_KM
        basis = "NOMINAL_VIIRS_I_BAND"
    return 500.0 * math.hypot(scan_km, track_km) + GEOLOCATION_BUFFER_M, basis


def snapshot_provider(mode: DataMode) -> str:
    # Fixtures never borrow real context, and real observations never see fixture facilities.
    return "TEST_FIXTURE" if mode == DataMode.SYNTHETIC_FIXTURE else PROVIDER


def summarize(candidates: list[dict], covered: bool) -> str:
    if not covered:
        return "CONTEXT_NOT_COVERED"
    inside = sum(1 for c in candidates if c["relation"] == "INSIDE_SUPPORT")
    if inside > 1:
        return "MULTIPLE_MAPPED_FEATURES"
    if inside == 1:
        return "SINGLE_MAPPED_FEATURE"
    return "NEARBY_ONLY" if candidates else "NO_MAPPED_FEATURE_NEARBY"


def observation_context(settings: Settings, observation_id: str, mode: DataMode) -> dict | None:
    with (
        database_engine(settings) as engine,
        engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn,
    ):
        obs = (
            conn.execute(
                text("""
            SELECT o.id,o.acquired_at,ST_X(o.geom) AS lon,ST_Y(o.geom) AS lat,
                (o.payload->>'scan_km')::double precision AS scan_km,
                (o.payload->>'track_km')::double precision AS track_km
            FROM observations o
            WHERE o.id=:id AND EXISTS (
                SELECT 1 FROM observation_receipts x JOIN ingestion_runs r ON r.id=x.run_id
                WHERE x.observation_id=o.id AND r.data_mode=:mode
                AND r.status IN ('SUCCEEDED','PARTIAL'))
        """),
                {"id": observation_id, "mode": mode.value},
            )
            .mappings()
            .first()
        )
        if obs is None:
            return None
        radius, basis = support_radius_m(obs["scan_km"], obs["track_km"])
        point = {"lon": obs["lon"], "lat": obs["lat"], "radius": radius}
        support = conn.execute(
            text("""
            SELECT ST_AsGeoJSON(ST_Buffer(ST_SetSRID(ST_Point(:lon,:lat),4326)::geography,
                :radius)::geometry, 7)
        """),
            point,
        ).scalar_one()
        snapshot = (
            conn.execute(
                text("""
            SELECT id,region_id,osm_base_at,first_received_at,facility_count,query_version,
                type_map_version,license,attribution
            FROM facility_snapshots
            WHERE provider=:provider AND ST_Covers(bounds,ST_SetSRID(ST_Point(:lon,:lat),4326))
            ORDER BY osm_base_at DESC,id LIMIT 1
        """),
                point | {"provider": snapshot_provider(mode)},
            )
            .mappings()
            .first()
        )
        candidates = []
        if snapshot is not None:
            rows = (
                conn.execute(
                    text("""
                WITH p AS (SELECT ST_SetSRID(ST_Point(:lon,:lat),4326) AS g),
                s AS (SELECT ST_Buffer(p.g::geography,:radius) AS support FROM p)
                SELECT f.osm_type,f.osm_id,f.name,f.facility_type,f.primary_tag,f.build,
                    f.osm_timestamp,
                    ST_Distance(p.g::geography,f.geom::geography) AS distance_m,
                    ST_Covers(f.geom,p.g) AS contains_centre,
                    CASE WHEN GeometryType(f.geom) IN ('POLYGON','MULTIPOLYGON')
                        AND ST_DWithin(p.g::geography,f.geom::geography,:radius)
                    THEN ST_Area(ST_Intersection(s.support,f.geom::geography))
                        / ST_Area(s.support) END AS support_overlap
                FROM facilities f,p,s
                WHERE f.snapshot_id=:snapshot
                    AND ST_DWithin(p.g::geography,f.geom::geography,:context_radius)
                ORDER BY distance_m,f.osm_type,f.osm_id
                LIMIT :cap
            """),
                    point
                    | {
                        "snapshot": snapshot["id"],
                        "context_radius": CONTEXT_RADIUS_M,
                        "cap": MAX_CANDIDATES + 1,
                    },
                )
                .mappings()
                .all()
            )
            for row in rows[:MAX_CANDIDATES]:
                distance = float(row["distance_m"])
                overlap = row["support_overlap"]
                candidates.append(
                    {
                        "osm_type": row["osm_type"],
                        "osm_id": row["osm_id"],
                        "osm_url": f"https://www.openstreetmap.org/{row['osm_type']}/{row['osm_id']}",
                        "name": row["name"],
                        "facility_type": row["facility_type"],
                        "primary_tag": row["primary_tag"],
                        "geometry_kind": row["build"],
                        "osm_last_edited_at": row["osm_timestamp"],
                        "distance_m": round(distance, 1),
                        "contains_pixel_centre": bool(row["contains_centre"]),
                        "support_overlap_fraction": (
                            None if overlap is None else round(min(float(overlap), 1.0), 4)
                        ),
                        "relation": "INSIDE_SUPPORT" if distance <= radius else "NEARBY",
                    }
                )
            truncated = len(rows) > MAX_CANDIDATES
        else:
            truncated = False
        event = observation_event(conn, observation_id, mode)
        land_cover = observation_landcover(conn, observation_id, obs["acquired_at"])
    in_support = [c for c in candidates if c["relation"] == "INSIDE_SUPPORT"]
    snapshot_block = None
    timing = None
    if snapshot is not None:
        snapshot_block = {
            "id": str(snapshot["id"]),
            "region_id": snapshot["region_id"],
            "osm_base_at": snapshot["osm_base_at"],
            "retrieved_at": snapshot["first_received_at"],
            "facility_count": snapshot["facility_count"],
            "query_version": snapshot["query_version"],
            "type_map_version": snapshot["type_map_version"],
            "license": snapshot["license"],
            "attribution": snapshot["attribution"],
        }
        timing = "RETROSPECTIVE" if snapshot["osm_base_at"] > obs["acquired_at"] else "PRIOR_STATE"
    return {
        "observation_id": obs["id"],
        "data_mode": mode.value,
        "acquired_at": obs["acquired_at"],
        "support_region": {
            "version": SUPPORT_VERSION,
            "shape": "APPROXIMATE_CIRCLE",
            "radius_m": round(radius, 1),
            "basis": basis,
            "geolocation_buffer_m": GEOLOCATION_BUFFER_M,
            "note": "Approximate area that could contain the pixel; not a fire perimeter.",
            "geometry": json.loads(support),
        },
        "facility_snapshot": snapshot_block,
        "context_timing": timing,
        "association": {
            "version": ASSOCIATION_VERSION,
            "status": summarize(candidates, snapshot is not None),
            "features_in_support": len(in_support),
            "facility_types_in_support": sorted({c["facility_type"] for c in in_support}),
            "context_radius_m": CONTEXT_RADIUS_M,
            "candidates": candidates,
            "candidates_truncated": truncated,
            "note": MISSINGNESS_NOTE,
        },
        "land_cover": land_cover,
        "event": event,
        "event_note": (
            "Not grouped yet: run the event builder for this region and mode."
            if event is None
            else "Grouped by time and distance only; an event is not a confirmed fire."
        ),
        "generated_at": datetime.now(UTC),
    }


def facilities_geojson(settings: Settings, bounds: Bounds, mode: DataMode) -> dict:
    params = bounds.model_dump() | {
        "provider": snapshot_provider(mode),
        "cap": MAX_MAP_FEATURES + 1,
    }
    with (
        database_engine(settings) as engine,
        engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn,
    ):
        snapshots = (
            conn.execute(
                text("""
            SELECT DISTINCT ON (region_id) id,region_id,osm_base_at,first_received_at,
                license,attribution
            FROM facility_snapshots
            WHERE provider=:provider
                AND bounds && ST_MakeEnvelope(:west,:south,:east,:north,4326)
            ORDER BY region_id,osm_base_at DESC,id
        """),
                params,
            )
            .mappings()
            .all()
        )
        rows = []
        if snapshots:
            rows = (
                conn.execute(
                    text("""
                SELECT f.snapshot_id,f.osm_type,f.osm_id,f.name,f.facility_type,f.primary_tag,
                    ST_AsGeoJSON(f.geom,6) AS geometry
                FROM facilities f
                WHERE f.snapshot_id = ANY(:snapshots)
                    AND f.geom && ST_MakeEnvelope(:west,:south,:east,:north,4326)
                ORDER BY f.snapshot_id,f.osm_type,f.osm_id
                LIMIT :cap
            """),
                    params | {"snapshots": [s["id"] for s in snapshots]},
                )
                .mappings()
                .all()
            )
    features = [
        {
            "type": "Feature",
            "id": f"{row['osm_type']}/{row['osm_id']}",
            "geometry": json.loads(row["geometry"]),
            "properties": {
                "osm_type": row["osm_type"],
                "osm_id": row["osm_id"],
                "name": row["name"],
                "facility_type": row["facility_type"],
                "primary_tag": row["primary_tag"],
                "snapshot_id": str(row["snapshot_id"]),
            },
        }
        for row in rows[:MAX_MAP_FEATURES]
    ]
    return {
        "type": "FeatureCollection",
        "features": features,
        "meta": {
            "bbox": list(bounds.model_dump().values()),
            "data_mode": mode.value,
            "truncated": len(rows) > MAX_MAP_FEATURES,
            "snapshots": [
                {
                    "id": str(s["id"]),
                    "region_id": s["region_id"],
                    "osm_base_at": s["osm_base_at"],
                    "retrieved_at": s["first_received_at"],
                    "license": s["license"],
                    "attribution": s["attribution"],
                }
                for s in snapshots
            ],
            "note": MISSINGNESS_NOTE,
        },
    }
