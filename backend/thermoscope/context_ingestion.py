"""One bounded OSM context run: immutable raw JSON, dated snapshot and validated geometry."""

import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from thermoscope.config import Settings
from thermoscope.database import database_engine
from thermoscope.firms import IngestError
from thermoscope.object_store import ObjectStore
from thermoscope.osm import (
    ATTRIBUTION,
    LICENSE,
    MAX_BYTES,
    PROVIDER,
    QUERY_VERSION,
    TYPE_MAP_VERSION,
    RejectedElement,
    build_query,
    fetch_overpass,
    parse_overpass,
)
from thermoscope.regions import REGIONS, Bounds

# PostGIS builds and repairs areas; anything that is still not a valid point or area is rejected.
GEOMETRY_SQL = """
    SELECT CASE
        WHEN :build = 'POINT' THEN src
        WHEN :build = 'RELATION_AREA' THEN ST_CollectionExtract(ST_MakeValid(ST_BuildArea(src)), 3)
        ELSE ST_CollectionExtract(ST_MakeValid(src), 3)
    END AS geom
    FROM (SELECT ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326) AS src) s
"""


def region_bounds(region_id: str) -> Bounds:
    for region in REGIONS:
        if region["id"] == region_id:
            return Bounds.parse(region["bbox"])
    raise IngestError("UNKNOWN_REGION")


def ingest_osm(
    settings: Settings,
    region_id: str,
    *,
    payload: bytes | None = None,
    expected_sha256: str | None = None,
    retrieved_at: datetime | None = None,
    endpoint: str | None = None,
    fetcher=fetch_overpass,
    provider: str = PROVIDER,
) -> dict:
    bounds = region_bounds(region_id)
    query = build_query(bounds)
    query_sha256 = hashlib.sha256(query.encode()).hexdigest()
    origin = "PROVIDER" if payload is None else "FILE"
    if origin == "FILE" and expected_sha256 is None:
        raise IngestError("FILE_HASH_REQUIRED")
    if retrieved_at is not None and (retrieved_at.tzinfo is None or origin == "PROVIDER"):
        raise IngestError("RETRIEVAL_TIME_INVALID")
    run_id = str(uuid4())
    started = datetime.now(UTC)
    store = ObjectStore(settings.object_store_local_path)
    scope = bounds.model_dump() | {
        "id": run_id,
        "provider": provider,
        "region": region_id,
        "query": query_sha256,
        "origin": origin,
        "started": started,
    }
    with database_engine(settings) as engine:
        with engine.begin() as conn:
            conn.execute(
                text("""
                INSERT INTO context_runs
                    (id,provider,region_id,bounds,query_sha256,origin,started_at,status)
                VALUES (:id,:provider,:region,ST_MakeEnvelope(:west,:south,:east,:north,4326),
                        :query,:origin,:started,'RUNNING')
            """),
                scope,
            )
        report = {"run_id": run_id, "status": "FAILED", "error_code": None}
        try:
            if payload is None:
                payload, endpoint = fetcher(query)
            received = datetime.now(UTC)
            first_received = retrieved_at.astimezone(UTC) if retrieved_at else received
            content_hash = hashlib.sha256(payload).hexdigest()
            if expected_sha256 is not None and content_hash != expected_sha256:
                raise IngestError("FILE_HASH_MISMATCH")
            if len(payload) > MAX_BYTES:
                raise IngestError("RESPONSE_TOO_LARGE")
            osm_base, facilities, rejected = parse_overpass(payload)
            if first_received < osm_base:
                raise IngestError("RETRIEVAL_BEFORE_OSM_BASE")
            store.save_raw(payload, suffix="json")
            store.save_manifest(
                run_id,
                {
                    "manifest_version": 1,
                    "kind": "facility_context",
                    "run_id": run_id,
                    "provider": provider,
                    "region_id": region_id,
                    "bounds": bounds.model_dump(),
                    "query_version": QUERY_VERSION,
                    "query_sha256": query_sha256,
                    "query": query,
                    "type_map_version": TYPE_MAP_VERSION,
                    "origin": origin,
                    "endpoint": endpoint,
                    "osm_base_at": osm_base.isoformat(),
                    "retrieved_at": first_received.isoformat(),
                    "retrieval_evidence": (
                        "OBSERVED_AT_FETCH"
                        if origin == "PROVIDER"
                        else ("OPERATOR_SUPPLIED" if retrieved_at else "FILE_IMPORT_TIME_ONLY")
                    ),
                    "imported_at": received.isoformat(),
                    "content_sha256": content_hash,
                    "raw_object": f"raw/{content_hash}.json",
                    "bytes": len(payload),
                    "license": LICENSE,
                    "attribution": ATTRIBUTION,
                    "timing_note": "OSM state at osm_base_at; applying it to earlier "
                    "observations is retrospective.",
                },
            )
            with engine.begin() as conn:
                snapshot_id = conn.execute(
                    text("""
                    INSERT INTO facility_snapshots
                        (id,provider,query_version,query_sha256,type_map_version,region_id,bounds,
                         content_sha256,osm_base_at,first_received_at,element_count,
                         facility_count,license,attribution)
                    VALUES (:id,:provider,:qv,:qs,:tv,:region,
                        ST_MakeEnvelope(:west,:south,:east,:north,4326),:hash,:base,:received,
                        :elements,0,:license,:attribution)
                    ON CONFLICT (provider,content_sha256)
                    DO UPDATE SET id = facility_snapshots.id RETURNING id
                """),
                    bounds.model_dump()
                    | {
                        "id": uuid4(),
                        "provider": provider,
                        "qv": QUERY_VERSION,
                        "qs": query_sha256,
                        "tv": TYPE_MAP_VERSION,
                        "region": region_id,
                        "hash": content_hash,
                        "base": osm_base,
                        "received": first_received,
                        "elements": len(facilities) + len(rejected),
                        "license": LICENSE,
                        "attribution": ATTRIBUTION,
                    },
                ).scalar_one()
                accepted = 0
                for item in facilities:
                    geom = conn.execute(
                        text(f"""
                        SELECT ST_AsEWKB(geom) FROM ({GEOMETRY_SQL}) g
                        WHERE geom IS NOT NULL AND NOT ST_IsEmpty(geom) AND ST_IsValid(geom)
                    """),
                        {"build": item.build, "geojson": json.dumps(item.geometry)},
                    ).scalar_one_or_none()
                    if geom is None:
                        rejected.append(
                            RejectedElement(item.osm_type, item.osm_id, "INVALID_GEOMETRY")
                        )
                        continue
                    conn.execute(
                        text("""
                        INSERT INTO facilities
                            (snapshot_id,osm_type,osm_id,osm_version,osm_timestamp,name,
                             facility_type,primary_tag,build,tags,geom)
                        VALUES (:snapshot,:osm_type,:osm_id,:version,:stamp,:name,:ftype,:tag,
                            :build,CAST(:tags AS jsonb),ST_GeomFromEWKB(:geom))
                        ON CONFLICT DO NOTHING
                    """),
                        {
                            "snapshot": snapshot_id,
                            "osm_type": item.osm_type,
                            "osm_id": item.osm_id,
                            "version": item.osm_version,
                            "stamp": item.osm_timestamp,
                            "name": item.name,
                            "ftype": item.facility_type,
                            "tag": item.primary_tag,
                            "build": item.build,
                            "tags": json.dumps(item.tags, sort_keys=True),
                            "geom": geom,
                        },
                    )
                    accepted += 1
                for row in rejected:
                    conn.execute(
                        text("""
                        INSERT INTO context_quarantine (run_id,osm_type,osm_id,reason)
                        VALUES (:run,:osm_type,:osm_id,:reason) ON CONFLICT DO NOTHING
                    """),
                        {
                            "run": run_id,
                            "osm_type": row.osm_type,
                            "osm_id": row.osm_id,
                            "reason": row.reason,
                        },
                    )
                conn.execute(
                    text("""
                    UPDATE facility_snapshots SET facility_count =
                        (SELECT count(*) FROM facilities WHERE snapshot_id=:snapshot)
                    WHERE id=:snapshot
                """),
                    {"snapshot": snapshot_id},
                )
                report.update(
                    status="PARTIAL" if rejected else "SUCCEEDED",
                    total_elements=accepted + len(rejected),
                    accepted_elements=accepted,
                    rejected_elements=len(rejected),
                    content_sha256=content_hash,
                    snapshot_id=str(snapshot_id),
                    osm_base_at=osm_base.isoformat(),
                )
                conn.execute(
                    text("""
                    UPDATE context_runs SET status=:status,snapshot_id=:snapshot,endpoint=:endpoint,
                        received_at=:received,completed_at=:completed,total_elements=:total,
                        accepted_elements=:accepted,rejected_elements=:rejected WHERE id=:run
                """),
                    {
                        "status": report["status"],
                        "snapshot": snapshot_id,
                        "endpoint": endpoint,
                        "received": received,
                        "completed": datetime.now(UTC),
                        "total": report["total_elements"],
                        "accepted": accepted,
                        "rejected": len(rejected),
                        "run": run_id,
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
                    UPDATE context_runs SET status='FAILED',error_code=:code,completed_at=:done
                    WHERE id=:id
                """),
                    {"code": report["error_code"], "done": datetime.now(UTC), "id": run_id},
                )
        return report
