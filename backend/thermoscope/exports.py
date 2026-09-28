"""Bounded evidence exports (P07-SUB-001, `evidence-export-v1`).

Two shapes, both built from stored data only (no provider call):

- a query window (region box, 1–31 days, data mode, product) as CSV or GeoJSON, one row or
  feature per satellite observation, optionally with the transparent rule outputs;
- one observation's evidence as GeoJSON: pixel centre, approximate pixel area, mapped facilities
  near it, the rule assessment, 180-day history and all provenance.

Oversized requests are refused, never silently truncated. Coordinates are WGS84 longitude and
latitude (RFC 7946); a point is a pixel centre, not a fire location or boundary. A missing value
stays empty/null, never zero. CSV text cells that a spreadsheet would run as a formula are
neutralised. Exports never contain credentials, reviewer identities or tokens, labels, or scores
from model runs: the learned model is not served and human validation is pending (ADR-024).
"""

import csv
import io
import json
import math
from datetime import UTC, date, datetime

from sqlalchemy import text

from thermoscope.assessment import observation_assessment, observation_timeline
from thermoscope.config import DataMode, Settings
from thermoscope.context import observation_context, support_radius_m
from thermoscope.database import database_engine
from thermoscope.observations import FILTER, query_params
from thermoscope.regions import Bounds, Product

EXPORT_VERSION = "evidence-export-v1"
MAX_OBSERVATIONS = 2000  # per window export
MAX_WITH_RULES = 100  # rule outputs are computed per observation (about 0.1 s each)
COORDINATES = "WGS84 (EPSG:4326) longitude and latitude in decimal degrees, as in RFC 7946"
LOCATION_MEANING = "PIXEL_CENTRE"
LOCATION_NOTE = (
    "Each point is the centre of a satellite pixel, not a fire location or boundary. The heat "
    "can lie anywhere within the approximate pixel area (pixel_support_radius_m)."
)
MISSING = (
    "Empty (CSV) or null (GeoJSON) means not supplied by the source or not computed; never zero."
)
LEARNED_MODEL = "NOT_SERVED: a trained model exists but has no reviewed labels to evaluate it."
HUMAN_VALIDATION = "PENDING: no reviewed labels exist; human validation is deferred (ADR-024)."
RULES = (
    "Transparent rules with uncalibrated thresholds (rules_version); not a trained model and not "
    "a probability. UNKNOWN means the evidence was insufficient or conflicting."
)
UNITS = {
    "frp_mw": "megawatts (fire radiative power)",
    "brightness_i4_k": "kelvin (I4 brightness temperature, not flame temperature)",
    "brightness_i5_k": "kelvin (I5 brightness temperature)",
    "scan_km": "kilometres (pixel size along scan)",
    "track_km": "kilometres (pixel size along track)",
    "pixel_support_radius_m": "metres (approximate pixel area radius incl. location buffer)",
    "acquired_at_utc": "ISO 8601, UTC (satellite acquisition)",
    "imported_at_utc": "ISO 8601, UTC (when this application stored the file)",
}


def firms_attribution(product: str, collection: str | None = None) -> str:
    return (
        f"NASA FIRMS, VIIRS 375 m active fire detections, {product}"
        + (f" (collection {collection})" if collection else "")
        + ". We acknowledge the use of data from NASA's Fire Information for Resource Management "
        "System (FIRMS), part of NASA's Earth Science Data and Information System (ESDIS). "
        "https://firms.modaps.eosdis.nasa.gov/"
    )


class ExportTooLarge(ValueError):
    def __init__(self, observations: int, limit: int, reason: str):
        super().__init__(reason)
        self.observations = observations
        self.limit = limit
        self.reason = reason


class Withheld(PermissionError):
    """Rule outputs are not exported from a blind-review server."""


def _iso(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _number(value):
    if value is None:
        return None
    number = float(value)
    return None if math.isnan(number) or math.isinf(number) else number


def window_rows(settings: Settings, bounds: Bounds, start: date, end: date, mode: DataMode,
                product: Product, include_rules: bool) -> tuple[list[dict], dict]:  # fmt: skip
    """Observation records for a validated window; refuses more than the export limits."""
    if include_rules and settings.review_only:
        raise Withheld("rule outputs are withheld on the blind-review server")
    params = query_params(bounds, start, end, mode, product)
    limit = MAX_WITH_RULES if include_rules else MAX_OBSERVATIONS
    with (
        database_engine(settings) as engine,
        engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn,
    ):
        total = conn.execute(
            text(f"SELECT count(*) FROM observations o WHERE {FILTER}"), params
        ).scalar_one()
        if total > limit:
            reason = (
                f"{total} observations match; exports with rule outputs are limited to {limit}"
                if include_rules
                else f"{total} observations match; window exports are limited to {limit}"
            )
            raise ExportTooLarge(total, limit, reason + ". Narrow the dates or the area.")
        rows = (
            conn.execute(
                text(f"""
            SELECT o.id,o.payload,ST_X(o.geom) AS lon,ST_Y(o.geom) AS lat,
                receipt.id AS run_id,receipt.received_at,receipt.row_number,
                s.content_sha256
            FROM observations o
            JOIN LATERAL (
                SELECT r.id,r.received_at,r.completed_at,x.row_number,r.snapshot_id
                FROM observation_receipts x JOIN ingestion_runs r ON r.id=x.run_id
                WHERE x.observation_id=o.id AND r.data_mode=:mode
                    AND r.status IN ('SUCCEEDED','PARTIAL')
                ORDER BY r.completed_at DESC,r.id,x.row_number LIMIT 1
            ) receipt ON true
            JOIN source_snapshots s ON s.id=receipt.snapshot_id
            WHERE {FILTER}
            ORDER BY o.acquired_at,o.id
        """),
                params,
            )
            .mappings()
            .all()
        )
    records = [observation_record(r, mode) for r in rows]
    if include_rules:
        for record in records:
            record |= rule_columns(
                observation_assessment(
                    settings, record["observation_id"], mode, None, "RETROSPECTIVE"
                )
            )
    meta = {
        "export_version": EXPORT_VERSION,
        "generated_at": _iso(datetime.now(UTC)),
        "query": {
            "bbox": list(bounds.model_dump().values()),
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "data_mode": mode.value,
            "product": product.value,
            "rule_outputs": include_rules,
        },
        "observations": len(records),
        "limits": {"observations": MAX_OBSERVATIONS, "with_rule_outputs": MAX_WITH_RULES},
    }
    return records, meta


def observation_record(row, mode: DataMode) -> dict:
    p = row["payload"]
    radius, basis = support_radius_m(p.get("scan_km"), p.get("track_km"))
    return {
        "observation_id": row["id"],
        "acquired_at_utc": _iso(datetime.fromisoformat(p["acquired_at"])),
        "latitude": _number(row["lat"]),
        "longitude": _number(row["lon"]),
        "location_meaning": LOCATION_MEANING,
        "pixel_support_radius_m": round(radius, 1),
        "pixel_support_basis": basis,
        "frp_mw": _number(p.get("frp_mw")),
        "brightness_i4_k": _number(p.get("brightness_i4_k")),
        "brightness_i5_k": _number(p.get("brightness_i5_k")),
        "scan_km": _number(p.get("scan_km")),
        "track_km": _number(p.get("track_km")),
        "daynight": p.get("daynight"),
        "nasa_confidence": p.get("source_confidence"),
        "satellite": p.get("satellite"),
        "sensor": p.get("sensor"),
        "product": p.get("product"),
        "collection_version": p.get("collection_version"),
        "data_mode": mode.value,
        "historical_availability": "KNOWN" if mode == DataMode.LIVE else "UNKNOWN",
        "raw_file_sha256": row["content_sha256"],
        "raw_row_number": row["row_number"],
        "ingestion_run_id": str(row["run_id"]),
        "imported_at_utc": _iso(row["received_at"]),
        "source_attribution": firms_attribution(p.get("product", ""), p.get("collection_version")),
    }


RULE_COLUMNS = [
    "rule_source",
    "rule_source_subtype",
    "rule_behaviour",
    "rule_review_priority",
    "rule_missing_or_limited",
    "rules_version",
    "rule_basis",
    "feature_snapshot_sha256",
]


def rule_columns(assessment: dict | None) -> dict:
    if assessment is None:
        return dict.fromkeys(RULE_COLUMNS)
    return {
        "rule_source": assessment["source"]["label"],
        "rule_source_subtype": assessment["source"].get("subtype"),
        "rule_behaviour": assessment["behaviour"]["label"],
        "rule_review_priority": assessment["priority"]["label"],
        "rule_missing_or_limited": "; ".join(assessment["missing_or_limited"]) or None,
        "rules_version": assessment["rules_version"],
        "rule_basis": assessment["basis"],
        "feature_snapshot_sha256": assessment["feature_snapshot_sha256"],
    }


BASE_COLUMNS = [
    "observation_id", "acquired_at_utc", "latitude", "longitude", "location_meaning",
    "pixel_support_radius_m", "pixel_support_basis", "frp_mw", "brightness_i4_k",
    "brightness_i5_k", "scan_km", "track_km", "daynight", "nasa_confidence", "satellite",
    "sensor", "product", "collection_version", "data_mode", "historical_availability",
    "raw_file_sha256", "raw_row_number", "ingestion_run_id", "imported_at_utc",
    "source_attribution",
]  # fmt: skip
STATUS_COLUMNS = ["learned_model", "human_validation"]
FORMULA_START = ("=", "+", "-", "@", "\t", "\r", "\n")


def csv_cell(value) -> str | float | int:
    """Numbers stay numbers; text a spreadsheet would evaluate gets a leading apostrophe."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return value
    value = str(value)
    return "'" + value if value.startswith(FORMULA_START) else value


def to_csv(records: list[dict], include_rules: bool) -> str:
    columns = BASE_COLUMNS + (RULE_COLUMNS if include_rules else []) + STATUS_COLUMNS
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(columns)
    status = {"learned_model": "NOT_SERVED", "human_validation": "PENDING"}
    for record in records:
        row = record | status
        writer.writerow([csv_cell(row.get(column)) for column in columns])
    return buffer.getvalue()


def to_geojson(records: list[dict], meta: dict) -> dict:
    features = []
    for record in records:
        properties = {k: v for k, v in record.items() if k not in {"latitude", "longitude"}}
        features.append(
            {
                "type": "Feature",
                "id": record["observation_id"],
                "geometry": {
                    "type": "Point",
                    "coordinates": [record["longitude"], record["latitude"]],
                },
                "properties": properties,
            }
        )
    return {"type": "FeatureCollection", "features": features, "meta": meta | describe()}


def describe() -> dict:
    return {
        "coordinates": COORDINATES,
        "geometry_meaning": LOCATION_NOTE,
        "units": UNITS,
        "missing_values": MISSING,
        "rules": RULES,
        "learned_model": LEARNED_MODEL,
        "human_validation": HUMAN_VALIDATION,
        "not_included": "credentials, reviewer identities or tokens, labels, model-run scores",
    }


def export_filename(bounds: Bounds, start: date, end: date, suffix: str) -> str:
    box = "_".join(f"{v:g}" for v in bounds.model_dump().values())
    return f"thermoscope-{box}-{start.isoformat()}-{end.isoformat()}.{suffix}"


def observation_evidence(
    settings: Settings, observation_id: str, mode: DataMode, basis: str
) -> dict | None:
    """One observation with everything the workbench shows about it, as GeoJSON."""
    if settings.review_only:
        raise Withheld("rule outputs are withheld on the blind-review server")
    context = observation_context(settings, observation_id, mode)
    if context is None:
        return None
    with (
        database_engine(settings) as engine,
        engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn,
    ):
        row = (
            conn.execute(
                text("""
            SELECT o.id,o.payload,ST_X(o.geom) AS lon,ST_Y(o.geom) AS lat,
                receipt.id AS run_id,receipt.received_at,receipt.row_number,s.content_sha256
            FROM observations o
            JOIN LATERAL (
                SELECT r.id,r.received_at,r.completed_at,x.row_number,r.snapshot_id
                FROM observation_receipts x JOIN ingestion_runs r ON r.id=x.run_id
                WHERE x.observation_id=o.id AND r.data_mode=:mode
                    AND r.status IN ('SUCCEEDED','PARTIAL')
                ORDER BY r.completed_at DESC,r.id,x.row_number LIMIT 1
            ) receipt ON true
            JOIN source_snapshots s ON s.id=receipt.snapshot_id
            WHERE o.id=:id
        """),
                {"id": observation_id, "mode": mode.value},
            )
            .mappings()
            .one()
        )
        snapshot = context["facility_snapshot"]
        geometries = {}
        candidates = context["association"]["candidates"]
        if snapshot and candidates:
            for g in conn.execute(
                text("""SELECT osm_type,osm_id,ST_AsGeoJSON(geom,7) AS geometry FROM facilities
                    WHERE snapshot_id=CAST(:s AS uuid)
                    AND (osm_type,osm_id) IN (SELECT * FROM unnest(CAST(:types AS text[]),
                        CAST(:ids AS bigint[])))"""),
                {
                    "s": snapshot["id"],
                    "types": [c["osm_type"] for c in candidates],
                    "ids": [c["osm_id"] for c in candidates],
                },  # fmt: skip
            ).mappings():
                geometries[(g["osm_type"], g["osm_id"])] = json.loads(g["geometry"])
    assessment = observation_assessment(settings, observation_id, mode, None, basis)
    timeline = observation_timeline(settings, observation_id, mode, 180, basis)
    record = observation_record(row, mode)
    support = context["support_region"]
    features = [
        {
            "type": "Feature",
            "id": observation_id,
            "geometry": {"type": "Point", "coordinates": [record["longitude"], record["latitude"]]},
            "properties": {"role": "PIXEL_CENTRE", "note": LOCATION_NOTE}
            | {k: v for k, v in record.items() if k not in {"latitude", "longitude"}}
            | rule_columns(assessment),
        },
        {
            "type": "Feature",
            "id": f"{observation_id}:pixel-area",
            "geometry": support["geometry"],
            "properties": {
                "role": "APPROXIMATE_PIXEL_AREA",
                "radius_m": support["radius_m"],
                "basis": support["basis"],
                "geolocation_buffer_m": support["geolocation_buffer_m"],
                "note": support["note"],
            },
        },
    ]
    for c in candidates:
        geometry = geometries.get((c["osm_type"], c["osm_id"]))
        if geometry is None:
            continue
        features.append(
            {
                "type": "Feature",
                "id": f"osm:{c['osm_type']}/{c['osm_id']}",
                "geometry": geometry,
                "properties": {"role": "MAPPED_CONTEXT_NOT_A_CONFIRMED_SOURCE"}
                | {k: _iso(v) if isinstance(v, datetime) else v for k, v in c.items()},
            }
        )
    land = context["land_cover"]
    sources = [{"source": "NASA FIRMS", "attribution": record["source_attribution"]}]
    if snapshot:
        sources.append(
            {
                "source": "OpenStreetMap",
                "license": snapshot["license"],
                "attribution": snapshot["attribution"],
                "as_of": _iso(snapshot["osm_base_at"]),
            }  # fmt: skip
        )
    if land:
        sources.append(
            {
                "source": "ESA WorldCover",
                "license": land["license"],
                "doi": land["doi"],
                "attribution": land["attribution"],
            }  # fmt: skip
        )
    history = None
    if timeline is not None:
        history = {
            "as_of": _iso(timeline["as_of"]),
            "basis": timeline["basis"],
            "radius_m": timeline["radius_m"],
            "days": [
                {
                    "date": d["date"].isoformat(),
                    "retrieved": d["retrieved"],
                    "detections": d["detections"] if d["retrieved"] else None,
                    "max_frp_mw": d["max_frp_mw"],
                }  # fmt: skip
                for d in timeline["days"]
            ],
            "note": timeline["note"],
        }
    meta = {
        "export_version": EXPORT_VERSION,
        "generated_at": _iso(datetime.now(UTC)),
        "observation_id": observation_id,
        "data_mode": mode.value,
        "assessment": None
        if assessment is None
        else {
            "basis": assessment["basis"],
            "as_of": _iso(assessment["as_of"]),
            "source": assessment["source"],
            "behaviour": assessment["behaviour"],
            "priority": assessment["priority"],
            "missing_or_limited": assessment["missing_or_limited"],
            "rules_version": assessment["rules_version"],
            "feature_version": assessment["feature_version"],
            "feature_snapshot_sha256": assessment["feature_snapshot_sha256"],
            "history_windows": assessment["features"]["windows"],
        },
        "history_180_days": history,
        "event": context["event"],
        "land_cover": land,
        "facility_snapshot": snapshot,
        "context_timing": context["context_timing"],
        "association": {k: v for k, v in context["association"].items() if k != "candidates"},
        "sources": sources,
    } | describe()
    return json.loads(
        json.dumps({"type": "FeatureCollection", "features": features, "meta": meta}, default=_iso)
    )
