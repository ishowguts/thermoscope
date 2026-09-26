"""One bounded ingestion run; immutable source objects and atomic deduplication."""

import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from thermoscope.config import DataMode, Settings
from thermoscope.database import database_engine
from thermoscope.firms import MAX_BYTES, IngestError, RejectedRow, fetch_csv, parse_csv
from thermoscope.object_store import ObjectStore
from thermoscope.regions import Window


def ingest(
    settings: Settings,
    window: Window,
    mode: DataMode,
    *,
    payload: bytes | None = None,
    expected_sha256: str | None = None,
    fetcher=fetch_csv,
) -> dict:
    origin = "PROVIDER" if payload is None else "FILE"
    if origin == "FILE" and mode == DataMode.LIVE:
        raise IngestError("FILE_IMPORT_CANNOT_BE_LIVE")
    if origin == "PROVIDER" and mode != DataMode.LIVE:
        raise IngestError("PROVIDER_FETCH_REQUIRES_LIVE_MODE")
    run_id = str(uuid4())
    started = datetime.now(UTC)
    if window.end_date > started.date():
        raise IngestError("FUTURE_WINDOW_NOT_ALLOWED")
    store = ObjectStore(settings.object_store_local_path)
    scope = window.bounds.model_dump()
    scope.update(
        id=run_id,
        product=window.product.value,
        start=window.start_date,
        end=window.end_date,
        mode=mode.value,
        origin=origin,
        started=started,
    )
    with database_engine(settings) as engine:
        with engine.begin() as conn:
            conn.execute(
                text("""
                INSERT INTO ingestion_runs
                    (id,product,bounds,start_date,end_date,data_mode,origin,started_at,status)
                VALUES (:id,:product,ST_MakeEnvelope(:west,:south,:east,:north,4326),
                        :start,:end,:mode,:origin,:started,'RUNNING')
            """),
                scope,
            )
        report = {"run_id": run_id, "status": "FAILED", "error_code": None}
        try:
            if payload is None:
                key = settings.firms_map_key.get_secret_value() if settings.firms_map_key else None
                payload = fetcher(key, window)
            received = datetime.now(UTC)
            content_hash = hashlib.sha256(payload).hexdigest()
            if expected_sha256 is not None and content_hash != expected_sha256:
                raise IngestError("FILE_HASH_MISMATCH")
            # Reject unsafe responses before either raw data or errors can persist a credential.
            if settings.firms_map_key and settings.firms_map_key.get_secret_value():
                if settings.firms_map_key.get_secret_value().encode() in payload:
                    raise IngestError("UNSAFE_PROVIDER_RESPONSE")
            if len(payload) > MAX_BYTES:
                raise IngestError("RESPONSE_TOO_LARGE")
            store.save_raw(payload)
            store.save_manifest(
                run_id,
                {
                    "manifest_version": 1,
                    "parser_version": "viirs-area-v1",
                    "run_id": run_id,
                    "provider": "NASA_FIRMS",
                    "product": window.product.value,
                    "bounds": window.bounds.model_dump(),
                    "start_date": str(window.start_date),
                    "end_date": str(window.end_date),
                    "data_mode": mode.value,
                    "origin": origin,
                    "received_at": received.isoformat(),
                    "content_sha256": content_hash,
                    "raw_object": f"raw/{content_hash}.csv",
                    "bytes": len(payload),
                    "availability_note": "Observed available at receipt"
                    if mode == DataMode.LIVE
                    else "Historical publication/availability unknown; file import time only",
                },
            )
            valid, rejected = parse_csv(payload, window, mode, received)
            total_rows = len(valid) + len(rejected)
            with engine.begin() as conn:
                snapshot_id = conn.execute(
                    text("""
                    INSERT INTO source_snapshots
                        (id,provider,product,content_sha256,data_mode,ingested_at)
                    VALUES (:id,'NASA_FIRMS',:product,:hash,:mode,:received)
                    ON CONFLICT (provider,product,content_sha256)
                    DO UPDATE SET id = source_snapshots.id RETURNING id
                """),
                    {
                        "id": uuid4(),
                        "product": window.product.value,
                        "hash": content_hash,
                        "mode": mode.value,
                        "received": received,
                    },
                ).scalar_one()
                inserted = accepted = 0
                for row in sorted(valid, key=lambda item: (item.identity, item.number)):
                    new_id = conn.execute(
                        text("""
                        INSERT INTO observations
                            (id,payload_sha256,product,acquired_at,first_ingested_at,geom,payload)
                        VALUES (:id,:hash,:product,:acquired,:received,
                            ST_SetSRID(ST_Point(:lon,:lat),4326),CAST(:payload AS jsonb))
                        ON CONFLICT (id) DO NOTHING RETURNING id
                    """),
                        {
                            "id": row.identity,
                            "hash": row.payload_hash,
                            "product": window.product.value,
                            "acquired": row.observation.times.acquired_at,
                            "received": received,
                            "lon": row.observation.longitude,
                            "lat": row.observation.latitude,
                            "payload": json.dumps(row.payload),
                        },
                    ).scalar_one_or_none()
                    if new_id is None:
                        previous = conn.execute(
                            text("SELECT payload_sha256 FROM observations WHERE id=:id"),
                            {"id": row.identity},
                        ).scalar_one()
                        if previous != row.payload_hash:
                            rejected.append(
                                RejectedRow(row.number, "SOURCE_REVISION_CONFLICT", row.raw)
                            )
                            continue
                    else:
                        inserted += 1
                    accepted += 1
                    conn.execute(
                        text("""
                        INSERT INTO observation_receipts (run_id,row_number,observation_id)
                        VALUES (:run,:number,:observation)
                    """),
                        {"run": run_id, "number": row.number, "observation": row.identity},
                    )
                for row in rejected:
                    conn.execute(
                        text("""
                        INSERT INTO quarantined_rows(run_id,row_number,reason,raw_row)
                        VALUES (:run,:number,:reason,CAST(:raw AS jsonb))
                    """),
                        {
                            "run": run_id,
                            "number": row.number,
                            "reason": row.reason,
                            "raw": json.dumps(row.raw),
                        },
                    )
                status = "PARTIAL" if rejected else "SUCCEEDED"
                report.update(
                    status=status,
                    total_rows=total_rows,
                    accepted_rows=accepted,
                    inserted_rows=inserted,
                    duplicate_rows=accepted - inserted,
                    rejected_rows=len(rejected),
                    content_sha256=content_hash,
                    snapshot_id=str(snapshot_id),
                )
                conn.execute(
                    text("""
                    UPDATE ingestion_runs SET status=:status,snapshot_id=:snapshot,
                        received_at=:received,completed_at=:completed,total_rows=:total_rows,
                        accepted_rows=:accepted_rows,inserted_rows=:inserted_rows,
                        rejected_rows=:rejected_rows WHERE id=:run_id
                """),
                    report
                    | {
                        "snapshot": snapshot_id,
                        "received": received,
                        "completed": datetime.now(UTC),
                    },
                )
        except (IngestError, OSError, SQLAlchemyError) as error:
            report = {"run_id": run_id, "status": "FAILED"}
            report["error_code"] = (
                error.code
                if isinstance(error, IngestError)
                else (
                    "OBJECT_STORE_UNAVAILABLE"
                    if isinstance(error, OSError)
                    else "DATABASE_WRITE_FAILED"
                )
            )
            with engine.begin() as conn:
                conn.execute(
                    text("""
                    UPDATE ingestion_runs SET status='FAILED',error_code=:code,
                        completed_at=:completed
                    WHERE id=:id
                """),
                    {"code": report["error_code"], "completed": datetime.now(UTC), "id": run_id},
                )
        return report
