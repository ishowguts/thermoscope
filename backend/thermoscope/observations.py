"""Bounded, read-only observation queries. Receipts preserve mode-specific provenance."""

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import text

from thermoscope.config import DataMode, Settings
from thermoscope.database import database_engine
from thermoscope.regions import REGIONS, Bounds, Product

FILTER = """
    o.product=:product AND o.geom && ST_MakeEnvelope(:west,:south,:east,:north,4326)
    AND o.acquired_at >= :start AND o.acquired_at < :end
    AND EXISTS (SELECT 1 FROM observation_receipts x JOIN ingestion_runs r ON r.id=x.run_id
                WHERE x.observation_id=o.id AND r.data_mode=:mode
                AND r.status IN ('SUCCEEDED','PARTIAL'))
"""


def query_params(bounds: Bounds, start: date, end: date, mode: DataMode, product: Product):
    if end < start or (end - start).days > 30 or end == date.max:
        raise ValueError("date range must contain 1 to 31 days")
    return bounds.model_dump() | {
        "start": datetime.combine(start, datetime.min.time(), UTC),
        "end": datetime.combine(end + timedelta(days=1), datetime.min.time(), UTC),
        "mode": mode.value,
        "product": product.value,
    }


def list_observations(settings, bounds, start, end, mode, product, limit, offset):
    params = query_params(bounds, start, end, mode, product) | {"limit": limit, "offset": offset}
    with (
        database_engine(settings) as engine,
        engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn,
    ):
        summary = (
            conn.execute(
                text(f"""
            SELECT count(*) AS total_observations, max(acquired_at) AS latest_acquisition_at
            FROM observations o WHERE {FILTER}
        """),
                params,
            )
            .mappings()
            .one()
        )
        rows = (
            conn.execute(
                text(f"""
            SELECT o.id,o.payload,o.first_ingested_at,ST_X(o.geom) AS lon,ST_Y(o.geom) AS lat,
                   receipt.id AS run_id,receipt.received_at,receipt.completed_at,
                   receipt.first_observed_at,
                   receipt.snapshot_id,receipt.row_number,s.content_sha256
            FROM observations o
            JOIN LATERAL (
                SELECT r.*,x.row_number,min(r.received_at) OVER () AS first_observed_at
                FROM observation_receipts x
                JOIN ingestion_runs r ON r.id=x.run_id
                WHERE x.observation_id=o.id AND r.data_mode=:mode
                  AND r.status IN ('SUCCEEDED','PARTIAL')
                ORDER BY r.completed_at DESC,r.id,x.row_number LIMIT 1
            ) receipt ON true
            JOIN source_snapshots s ON s.id=receipt.snapshot_id
            WHERE {FILTER}
            ORDER BY o.acquired_at DESC,o.id ASC LIMIT :limit OFFSET :offset
        """),
                params,
            )
            .mappings()
            .all()
        )
        latest = (
            conn.execute(
                text("""
            SELECT id,status,origin,started_at,received_at,completed_at,total_rows,
                accepted_rows,inserted_rows,rejected_rows,error_code
            FROM ingestion_runs
            WHERE product=:product AND data_mode=:mode
                AND start_date < CAST(:end AS date) AND end_date >= CAST(:start AS date)
                AND ST_Covers(bounds,ST_MakeEnvelope(:west,:south,:east,:north,4326))
            ORDER BY started_at DESC,id LIMIT 1
        """),
                params,
            )
            .mappings()
            .first()
        )
    features = []
    for row in rows:
        props = dict(row["payload"])
        props.update(
            {
                "data_mode": mode.value,
                "first_ingested_at": row["first_ingested_at"],
                "ingested_at": row["received_at"],
                "run_completed_at": row["completed_at"],
                "source_published_at": None,
                "first_available_at": row["first_observed_at"] if mode == DataMode.LIVE else None,
                "availability_evidence": "KNOWN" if mode == DataMode.LIVE else "UNKNOWN",
                "availability_basis": "OBSERVED_AT_FETCH" if mode == DataMode.LIVE else "UNKNOWN",
                "snapshot_id": str(row["snapshot_id"]),
                "run_id": str(row["run_id"]),
                "raw_sha256": row["content_sha256"],
                "raw_row_number": row["row_number"],
            }
        )
        features.append(
            {
                "type": "Feature",
                "id": row["id"],
                "geometry": {"type": "Point", "coordinates": [row["lon"], row["lat"]]},
                "properties": props,
            }
        )
    total = summary["total_observations"]
    return {
        "type": "FeatureCollection",
        "features": features,
        "meta": {
            "data_mode": mode.value,
            "product": product.value,
            "bbox": list(bounds.model_dump().values()),
            "start_date": start,
            "end_date": end,
            "limit": limit,
            "offset": offset,
            "total_observations": total,
            "next_offset": offset + limit
            if offset + limit < total and offset + limit <= 10000
            else None,
            "pagination_capped": offset + limit < total and offset + limit > 10000,
            "latest_acquisition_at": summary["latest_acquisition_at"],
            "latest_run": dict(latest) if latest else None,
            "classification_status": "NOT_IMPLEMENTED",
            "generated_at": datetime.now(UTC),
        },
    }


def catalog(settings: Settings, mode: DataMode, product: Product):
    regions = []
    with database_engine(settings) as engine, engine.connect() as conn:
        for region in REGIONS:
            params = Bounds.parse(region["bbox"]).model_dump() | {
                "mode": mode.value,
                "product": product.value,
            }
            row = (
                conn.execute(
                    text("""
                SELECT min(o.acquired_at) AS first_at,max(o.acquired_at) AS last_at,
                    count(*) AS count
                FROM observations o
                WHERE o.product=:product
                    AND o.geom && ST_MakeEnvelope(:west,:south,:east,:north,4326)
                    AND EXISTS (SELECT 1 FROM observation_receipts x
                        JOIN ingestion_runs r ON r.id=x.run_id WHERE x.observation_id=o.id
                        AND r.data_mode=:mode AND r.status IN ('SUCCEEDED','PARTIAL'))
            """),
                    params,
                )
                .mappings()
                .one()
            )
            end = row["last_at"].date() if row["last_at"] else datetime.now(UTC).date()
            first = row["first_at"].date() if row["first_at"] else end - timedelta(days=4)
            regions.append(
                region
                | {
                    "start_date": max(first, end - timedelta(days=30)),
                    "end_date": end,
                    "total_stored": row["count"],
                }
            )
    return {"regions": regions, "data_mode": mode.value, "product": product.value}
