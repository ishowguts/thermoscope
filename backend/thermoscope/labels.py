"""P05 labels: frozen case sets and splits, independent registry evidence, blind reviews.

Integrity rules enforced here:
- Splits are frozen from site groups before any label exists; a site never spans two splits.
- Reviewers never see rule outputs, weak/silver labels or model predictions (blind review).
- GOLD needs human review with cited evidence; test cases need two agreeing reviews or an
  adjudication. SILVER is registry corroboration without review. WEAK is this project's own
  rules and can assist training but never certify a test case.
"""

import csv
import hashlib
import io
import json
import re
from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import text

from thermoscope.config import DataMode, Settings
from thermoscope.database import batch_engine, database_engine
from thermoscope.events import ALGORITHM_VERSION, build_event_run
from thermoscope.firms import IngestError
from thermoscope.object_store import ObjectStore
from thermoscope.regions import NOAA20_FAMILY, REGIONS

CASE_VERSION = "case-v1"
FEATURE_VERSION = "case-features-v1"
LABEL_POLICY = "label-resolution-v1"
SPLIT_SEED = "thermoscope-p05-split-v1"
SPLIT_FRACTIONS = {"TRAIN": 0.6, "VALIDATION": 0.2, "TEST": 0.2}
GROUP_MERGE_M = 2000.0
FORWARD_CUTOFF = datetime(2026, 8, 15, tzinfo=UTC)
REGISTRY_MATCH_M = 1500.0
SOURCE_LABELS = ("INDUSTRIAL", "VEGETATION_FIRE", "AGRICULTURAL_BURN", "OTHER", "UNRESOLVED")
SUBTYPES = ("GAS_FLARE", "OTHER_PERSISTENT_HEAT", "MINING_HEAT", "UNRESOLVED")
GPPD = {
    "id": "WRI_GPPD_1_3_0",
    "name": "Global Power Plant Database",
    "version": "1.3.0",
    "license": "CC-BY-4.0",
    "attribution": "Global Power Plant Database v1.3.0, World Resources Institute and partners "
    "(CC BY 4.0)",
    "url": "https://github.com/wri/global-power-plant-database",
    "data_year": 2021,
}
THERMAL_FUELS = {"Coal", "Gas", "Oil", "Biomass", "Petcoke", "Cogeneration", "Waste"}


def stable_hash(*parts) -> str:
    return hashlib.sha256("\x1f".join(str(p) for p in parts).encode()).hexdigest()


# ---------------------------------------------------------------------------------------------
# Independent registry evidence


def import_gppd(settings: Settings, payload: bytes, expected_sha256: str, retrieved_at: datetime):
    digest = hashlib.sha256(payload).hexdigest()
    if digest != expected_sha256:
        raise IngestError("FILE_HASH_MISMATCH")
    if retrieved_at.tzinfo is None:
        raise IngestError("RETRIEVAL_TIME_INVALID")
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8")))
    needed = {"country", "gppd_idnr", "name", "latitude", "longitude", "primary_fuel"}
    if not needed.issubset(reader.fieldnames or []):
        raise IngestError("UNSUPPORTED_REGISTRY_SCHEMA")
    records, skipped = [], 0
    for row in reader:
        if row["country"] != "IND" or row["primary_fuel"] not in THERMAL_FUELS:
            continue
        try:
            lat, lon = float(row["latitude"]), float(row["longitude"])
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                raise ValueError
        except ValueError:
            skipped += 1
            continue

        def number(value):
            try:
                return float(value) if value not in (None, "") else None
            except ValueError:
                return None

        records.append(
            {
                "source": GPPD["id"],
                "record": row["gppd_idnr"],
                "name": row["name"][:200],
                "category": "THERMAL_POWER_PLANT",
                "fuel": row["primary_fuel"],
                "capacity": number(row.get("capacity_mw")),
                "year": number(row.get("commissioning_year")),
                "lon": lon,
                "lat": lat,
            }
        )
    store = ObjectStore(settings.object_store_local_path)
    store.save_raw(payload, suffix="csv")
    with database_engine(settings) as engine, engine.begin() as conn:
        existing = conn.execute(
            text("SELECT content_sha256 FROM registry_sources WHERE id=:id FOR UPDATE"),
            {"id": GPPD["id"]},
        ).scalar()
        if existing is not None and existing != digest:
            # One file per registry version: a different file under the same version is refused.
            raise IngestError("REGISTRY_VERSION_CONFLICT")
        conn.execute(
            text("""
            INSERT INTO registry_sources (id,name,version,license,attribution,url,content_sha256,
                data_year,retrieved_at,imported_at)
            VALUES (:id,:name,:version,:license,:attribution,:url,:sha,:year,:retrieved,:now)
            ON CONFLICT (id) DO NOTHING
        """),
            {
                **{k: GPPD[k] for k in ("id", "name", "version", "license", "attribution", "url")},
                "sha": digest,
                "year": GPPD["data_year"],
                "retrieved": retrieved_at,
                "now": datetime.now(UTC),
            },
        )
        for r in records:
            conn.execute(
                text("""
                INSERT INTO registry_facilities (source_id,record_id,name,category,fuel,
                    capacity_mw,commissioning_year,geom)
                VALUES (:source,:record,:name,:category,:fuel,:capacity,:year,
                    ST_SetSRID(ST_Point(:lon,:lat),4326))
                ON CONFLICT DO NOTHING
            """),
                r,
            )
    return {"source": GPPD["id"], "records": len(records), "skipped": skipped, "sha256": digest}


def registry_matches(conn, lon: float, lat: float, radius=REGISTRY_MATCH_M) -> list[dict]:
    rows = conn.execute(
        text("""
        SELECT f.source_id,f.record_id,f.name,f.category,f.fuel,f.capacity_mw,
            ST_Distance(f.geom::geography,ST_SetSRID(ST_Point(:lon,:lat),4326)::geography) AS d,
            s.attribution,s.version
        FROM registry_facilities f JOIN registry_sources s ON s.id=f.source_id
        WHERE ST_DWithin(f.geom::geography,ST_SetSRID(ST_Point(:lon,:lat),4326)::geography,:r)
        ORDER BY d,f.source_id,f.record_id LIMIT 5
    """),
        {"lon": lon, "lat": lat, "r": radius},
    ).mappings()
    return [
        {
            "source": r["source_id"],
            "record_id": r["record_id"],
            "name": r["name"],
            "category": r["category"],
            "fuel": r["fuel"],
            "capacity_mw": r["capacity_mw"],
            "distance_m": round(float(r["d"]), 1),
            "attribution": r["attribution"],
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------------------------
# Frozen case sets and splits


def union_groups(site_ids: list[str], close_pairs: list[tuple[str, str]]) -> dict[str, str]:
    """Sites within the merge distance share one group, named after its smallest site ID."""
    parent = {s: s for s in site_ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in close_pairs:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    return {s: find(s) for s in site_ids}


def assign_splits(cases: list[dict]) -> dict[str, str]:
    """Per region, order groups by a seeded hash and fill TRAIN, VALIDATION, TEST by case count."""
    by_region = defaultdict(lambda: defaultdict(int))
    for c in cases:
        by_region[c["region_id"]][c["split_group"]] += 1
    assignment = {}
    for _region, groups in sorted(by_region.items()):
        total = sum(groups.values())
        ordered = sorted(groups, key=lambda g: stable_hash(SPLIT_SEED, g))
        running = 0
        for group in ordered:
            share = running / total if total else 0
            if share < SPLIT_FRACTIONS["TRAIN"]:
                split = "TRAIN"
            elif share < SPLIT_FRACTIONS["TRAIN"] + SPLIT_FRACTIONS["VALIDATION"]:
                split = "VALIDATION"
            else:
                split = "TEST"
            assignment[group] = split
            running += groups[group]
        # A region with at least three groups always contributes to every split.
        if len(ordered) >= 3 and "TEST" not in {assignment[g] for g in ordered}:
            assignment[ordered[-1]] = "TEST"
        if len(ordered) >= 3 and "VALIDATION" not in {assignment[g] for g in ordered}:
            assignment[ordered[-2]] = "VALIDATION"
    return assignment


REVIEW_ORDER = "split-interleaved-v1"
REVIEW_PATTERN = ("TEST", "TRAIN", "VALIDATION", "TEST", "TRAIN")


def review_order(cases: list[dict]) -> list[str]:
    """Splits take turns (TEST, TRAIN, VALIDATION, TEST, TRAIN, ...) so that a small labelling
    effort reaches every split. Within a split, regions take turns and each region offers one
    case per site group before repeating a group, so early reviews are diverse."""
    streams = {}
    for split in ("TEST", "VALIDATION", "TRAIN"):
        regions = defaultdict(lambda: defaultdict(list))
        for c in cases:
            if c["split"] == split:
                regions[c["region_id"]][c["split_group"]].append(c["id"])
        per_region = []
        for _, groups in sorted(regions.items()):
            lanes = [
                sorted(ids, key=lambda i: stable_hash(SPLIT_SEED, "rank", i))
                for _, ids in sorted(groups.items(), key=lambda kv: stable_hash(SPLIT_SEED, kv[0]))
            ]
            stream = []
            while any(lanes):
                for lane in lanes:
                    if lane:
                        stream.append(lane.pop(0))
            per_region.append(stream)
        merged = []
        while any(per_region):
            for stream in per_region:
                if stream:
                    merged.append(stream.pop(0))
        streams[split] = merged[::-1]  # reversed so pop() takes the next case cheaply
    order = []
    while any(streams.values()):
        for split in REVIEW_PATTERN:
            if streams[split]:
                order.append(streams[split].pop())
    return order


def build_case_set(settings: Settings, name: str, mode: DataMode) -> dict:
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{2,60}", name):
        raise IngestError("INVALID_CASE_SET_NAME")
    runs = {}
    for region in REGIONS:
        report = build_event_run(settings, region["id"], mode)
        runs[region["id"]] = report["run_id"]
    with batch_engine(settings) as engine, engine.begin() as conn:
        if conn.execute(text("SELECT 1 FROM case_sets WHERE name=:n"), {"n": name}).first():
            raise IngestError("CASE_SET_EXISTS")
        rows = (
            conn.execute(
                text("""
            SELECT e.id,e.run_id,e.site_id,e.started_at,e.ended_at,e.observation_count,r.region_id,
                rep.observation_id AS rep_id,ST_X(o.geom) AS lon,ST_Y(o.geom) AS lat
            FROM events e JOIN event_runs r ON r.id=e.run_id
            JOIN LATERAL (
                SELECT x.observation_id FROM event_observations x
                JOIN observations ob ON ob.id=x.observation_id
                WHERE x.run_id=e.run_id AND x.event_id=e.id
                ORDER BY (ob.payload->>'frp_mw')::double precision DESC NULLS LAST,
                    ob.acquired_at,ob.id LIMIT 1
            ) rep ON true
            JOIN observations o ON o.id=rep.observation_id
            WHERE e.run_id = ANY(:runs)
            ORDER BY r.region_id,e.started_at,e.id
        """),
                {"runs": list(runs.values())},
            )
            .mappings()
            .all()
        )
        if not rows:
            raise IngestError("NO_EVENTS")
        close = conn.execute(
            text("""
            SELECT a.id,b.id FROM sites a JOIN sites b
                ON a.run_id = ANY(:runs) AND b.run_id = ANY(:runs) AND a.id < b.id
                AND ST_DWithin(ST_Centroid(a.geom)::geography,ST_Centroid(b.geom)::geography,:d)
        """),
            {"runs": list(runs.values()), "d": GROUP_MERGE_M},
        ).all()
        groups = union_groups(sorted({r["site_id"] for r in rows}), [tuple(p) for p in close])
        cases = [
            {
                "id": r["id"],
                "event_run_id": r["run_id"],
                "event_id": r["id"],
                "site_id": r["site_id"],
                "split_group": groups[r["site_id"]],
                "region_id": r["region_id"],
                "as_of": r["ended_at"],
                "started_at": r["started_at"],
                "observation_count": r["observation_count"],
                "rep": r["rep_id"],
                "lon": r["lon"],
                "lat": r["lat"],
            }
            for r in rows
        ]
        splits = assign_splits(cases)
        for c in cases:
            c["split"] = splits[c["split_group"]]
            c["forward_period"] = "BEFORE" if c["as_of"] < FORWARD_CUTOFF else "AFTER"
            c["review_slots"] = 2 if c["split"] == "TEST" else 1
        ranks = {case_id: i for i, case_id in enumerate(review_order(cases))}
        policy = {
            "case_version": CASE_VERSION,
            "event_algorithm": ALGORITHM_VERSION,
            "seed": SPLIT_SEED,
            "fractions": SPLIT_FRACTIONS,
            "group_merge_m": GROUP_MERGE_M,
            "protocols": {
                "UNSEEN_SITE": "site-group-disjoint TRAIN / VALIDATION / TEST within each region",
                "KNOWN_SITE_FUTURE": f"train on as_of < {FORWARD_CUTOFF.isoformat()}, test on "
                "later cases at sites seen in training",
            },
            "forward_cutoff": FORWARD_CUTOFF.isoformat(),
            "test_review_slots": 2,
            "review_order": REVIEW_ORDER,
        }
        manifest = {
            "name": name,
            "data_mode": mode.value,
            "stream": NOAA20_FAMILY,
            "policy": policy,
            "event_runs": runs,
            "cases": [[c["id"], c["split"], c["split_group"]] for c in cases],
        }
        manifest_bytes = json.dumps(manifest, sort_keys=True, default=str).encode()
        manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
        set_id = uuid4()
        ObjectStore(settings.object_store_local_path).put_once(
            f"manifests/case-set-{set_id}.json", manifest_bytes + b"\n"
        )
        conn.execute(
            text("""
            INSERT INTO case_sets (id,name,data_mode,case_version,split_policy,event_runs,
                case_count,manifest_sha256,created_at)
            VALUES (:id,:name,:mode,:version,CAST(:policy AS jsonb),CAST(:runs AS jsonb),
                :count,:sha,:now)
        """),
            {
                "id": set_id,
                "name": name,
                "mode": mode.value,
                "version": CASE_VERSION,
                "policy": json.dumps(policy),
                "runs": json.dumps(runs),
                "count": len(cases),
                "sha": manifest_sha,
                "now": datetime.now(UTC),
            },
        )
        for c in cases:
            conn.execute(
                text("""
                INSERT INTO label_cases (case_set_id,id,event_run_id,event_id,site_id,
                    split_group,split,forward_period,region_id,as_of,started_at,
                    observation_count,representative_observation_id,geom,review_slots,review_rank)
                VALUES (:set,:id,:event_run_id,:event_id,:site_id,:split_group,:split,
                    :forward_period,:region_id,:as_of,:started_at,:observation_count,:rep,
                    ST_SetSRID(ST_Point(:lon,:lat),4326),:review_slots,:rank)
            """),
                c | {"set": set_id, "rank": ranks[c["id"]]},
            )
    counts = defaultdict(int)
    for c in cases:
        counts[c["split"]] += 1
    return {
        "case_set_id": str(set_id),
        "name": name,
        "cases": len(cases),
        "site_groups": len(set(groups.values())),
        "splits": dict(sorted(counts.items())),
        "manifest_sha256": manifest_sha,
    }


def list_case_sets(settings: Settings) -> list[dict]:
    with database_engine(settings) as engine, engine.connect() as conn:
        rows = conn.execute(
            text("""
            SELECT s.id,s.name,s.data_mode,s.case_count,s.manifest_sha256,s.created_at,
                (SELECT count(*) FROM label_reviews r WHERE r.case_set_id=s.id) AS reviews
            FROM case_sets s ORDER BY s.created_at DESC
        """)
        ).mappings()
        return [dict(r) | {"id": str(r["id"])} for r in rows]


def case_set_id(conn, name_or_id: str) -> UUID:
    row = conn.execute(
        text("SELECT id FROM case_sets WHERE name=:v OR CAST(id AS text)=:v"), {"v": name_or_id}
    ).first()
    if row is None:
        raise IngestError("UNKNOWN_CASE_SET")
    return row[0]


# ---------------------------------------------------------------------------------------------
# Label resolution


def resolve_label(reviews: list[dict], review_slots: int, silver: str | None, weak: str | None):
    """Deterministic tiering from blind reviews, registry corroboration and rules."""
    adjudications = [r for r in reviews if r["role"] == "ADJUDICATOR"]
    reviewers = [r for r in reviews if r["role"] == "REVIEWER"]
    if adjudications:
        a = adjudications[-1]
        tier = "GOLD" if a["evidence"] else "SILVER"
        if a["source_label"] == "UNRESOLVED":
            return {"label": "UNRESOLVED", "tier": "UNRESOLVED", "basis": "ADJUDICATED_UNRESOLVED"}
        return {"label": a["source_label"], "tier": tier, "basis": "ADJUDICATED"}
    if reviewers:
        labels = {r["source_label"] for r in reviewers}
        cited = any(r["evidence"] for r in reviewers)
        if len(reviewers) >= 2:
            if len(labels) > 1:
                return {"label": "UNRESOLVED", "tier": "UNRESOLVED",
                        "basis": "DISAGREEMENT_PENDING_ADJUDICATION"}  # fmt: skip
            label = labels.pop()
            if label == "UNRESOLVED":
                return {"label": "UNRESOLVED", "tier": "UNRESOLVED", "basis": "REVIEWERS_UNSURE"}
            return {"label": label, "tier": "GOLD" if cited else "SILVER",
                    "basis": "TWO_REVIEWERS_AGREE"}  # fmt: skip
        label = reviewers[0]["source_label"]
        if label == "UNRESOLVED":
            return {"label": "UNRESOLVED", "tier": "UNRESOLVED", "basis": "REVIEWER_UNSURE"}
        if review_slots >= 2:
            return {"label": label, "tier": "SILVER", "basis": "ONE_OF_TWO_REVIEWS"}
        return {"label": label, "tier": "GOLD" if cited else "SILVER", "basis": "ONE_REVIEWER"}
    if silver:
        return {"label": silver, "tier": "SILVER", "basis": "REGISTRY_CORROBORATED"}
    if weak and weak != "UNKNOWN":
        return {"label": weak, "tier": "WEAK", "basis": "RULES"}
    return {"label": None, "tier": None, "basis": "UNLABELLED"}


def eligible_for_test(resolved: dict) -> bool:
    return resolved["tier"] == "GOLD" and resolved["basis"] in {
        "TWO_REVIEWERS_AGREE",
        "ADJUDICATED",
    }


def resolved_labels(conn, set_id) -> dict[str, dict]:
    reviews = defaultdict(list)
    for r in conn.execute(
        text("""
        SELECT case_id,role,source_label,evidence,reviewer,reviewed_at FROM label_reviews
        WHERE case_set_id=:s ORDER BY reviewed_at,id
    """),
        {"s": set_id},
    ).mappings():
        reviews[r["case_id"]].append(dict(r))
    out = {}
    for c in conn.execute(
        text("""
        SELECT c.id,c.split,c.review_slots,f.silver_label,f.weak_label
        FROM label_cases c LEFT JOIN case_features f
            ON f.case_set_id=c.case_set_id AND f.case_id=c.id AND f.feature_version=:v
        WHERE c.case_set_id=:s
    """),
        {"s": set_id, "v": FEATURE_VERSION},
    ).mappings():
        resolved = resolve_label(
            reviews[c["id"]], c["review_slots"], c["silver_label"], c["weak_label"]
        )
        resolved["split"] = c["split"]
        resolved["test_eligible"] = eligible_for_test(resolved)
        resolved["reviews"] = len(reviews[c["id"]])
        out[c["id"]] = resolved
    return out


# ---------------------------------------------------------------------------------------------
# Blind review API support

URL = re.compile(r"^https?://[^\s<>\"']{4,490}$")


def external_links(lon: float, lat: float, day) -> list[dict]:
    d = 0.08
    box = f"{lon - d:.4f},{lat - d:.4f},{lon + d:.4f},{lat + d:.4f}"
    layers = "VIIRS_NOAA20_CorrectedReflectance_TrueColor,VIIRS_NOAA20_Thermal_Anomalies_375m_All"
    return [
        {
            "label": "NASA Worldview on the event date (true colour + thermal anomalies)",
            "url": f"https://worldview.earthdata.nasa.gov/?v={box}&t={day}&l={layers}",
        },
        {
            "label": "Satellite basemap (Google Maps)",
            "url": f"https://www.google.com/maps/@{lat:.5f},{lon:.5f},1200m/data=!3m1!1e3",
        },
        {
            "label": "OpenStreetMap",
            "url": f"https://www.openstreetmap.org/?mlat={lat:.5f}&mlon={lon:.5f}#map=15/{lat:.5f}/{lon:.5f}",
        },
    ]


def review_queue(settings: Settings, set_ref: str, reviewer: str, limit: int = 20) -> dict:
    with database_engine(settings) as engine, engine.connect() as conn:
        set_id = case_set_id(conn, set_ref)
        labels = resolved_labels(conn, set_id)
        rows = (
            conn.execute(
                text("""
            SELECT c.id,c.split,c.region_id,c.as_of,c.review_slots,c.review_rank,
                COUNT(r.id) FILTER (WHERE r.role='REVIEWER') AS reviews,
                BOOL_OR(lower(r.reviewer)=lower(:who)) AS mine
            FROM label_cases c LEFT JOIN label_reviews r
                ON r.case_set_id=c.case_set_id AND r.case_id=c.id
            WHERE c.case_set_id=:s
            GROUP BY c.id,c.split,c.region_id,c.as_of,c.review_slots,c.review_rank
            ORDER BY c.review_rank
        """),
                {"s": set_id, "who": reviewer},
            )
            .mappings()
            .all()
        )
    adjudicate, review = [], []
    for r in rows:
        if r["mine"]:
            continue
        basis = labels[r["id"]]["basis"]
        item = {
            "case_id": r["id"],
            "split": r["split"],
            "region_id": r["region_id"],
            "as_of": r["as_of"],
            "reviews": r["reviews"],
            "needs": r["review_slots"],
        }
        if basis == "DISAGREEMENT_PENDING_ADJUDICATION":
            adjudicate.append(item | {"role": "ADJUDICATOR"})
        elif r["reviews"] < r["review_slots"]:
            review.append(item | {"role": "REVIEWER"})
    return {
        "case_set_id": str(set_id),
        "reviewer": reviewer,
        "adjudication": adjudicate[:limit],
        "review": review[:limit],
        "remaining_reviews": len(review),
        "remaining_adjudications": len(adjudicate),
    }


def review_case(settings: Settings, set_ref: str, case_id: str) -> dict | None:
    """Evidence for a blind review: no rule, weak/silver label or model output."""
    from thermoscope.context import (
        find_candidates,
        find_snapshot,
        snapshot_provider,
        support_radius_m,
    )

    with database_engine(settings) as engine, engine.connect() as conn:
        set_id = case_set_id(conn, set_ref)
        case = (
            conn.execute(
                text("""
            SELECT c.*,ST_X(c.geom) AS lon,ST_Y(c.geom) AS lat,s.data_mode
            FROM label_cases c JOIN case_sets s ON s.id=c.case_set_id
            WHERE c.case_set_id=:s AND c.id=:id
        """),
                {"s": set_id, "id": case_id},
            )
            .mappings()
            .first()
        )
        if case is None:
            return None
        members = (
            conn.execute(
                text("""
            SELECT o.id,o.acquired_at,ST_X(o.geom) AS lon,ST_Y(o.geom) AS lat,
                (o.payload->>'frp_mw')::double precision AS frp_mw,
                o.payload->>'daynight' AS daynight,o.payload->>'source_confidence' AS confidence,
                o.product,(o.payload->>'scan_km')::double precision AS scan_km,
                (o.payload->>'track_km')::double precision AS track_km
            FROM event_observations x JOIN observations o ON o.id=x.observation_id
            WHERE x.run_id=:run AND x.event_id=:event ORDER BY o.acquired_at,o.id
        """),
                {"run": case["event_run_id"], "event": case["event_id"]},
            )
            .mappings()
            .all()
        )
        rep = next(m for m in members if m["id"] == case["representative_observation_id"])
        radius, _ = support_radius_m(rep["scan_km"], rep["track_km"])
        snapshot = find_snapshot(
            conn, case["lon"], case["lat"], snapshot_provider(DataMode(case["data_mode"]))
        )
        candidates = []
        if snapshot:
            candidates, _ = find_candidates(conn, case["lon"], case["lat"], radius, snapshot["id"])
        registry = registry_matches(conn, case["lon"], case["lat"], radius=5000)
        from thermoscope.landcover import observation_landcover

        land = observation_landcover(conn, rep["id"], rep["acquired_at"])
        prior = [
            dict(r)
            for r in conn.execute(
                text("""SELECT role,source_label,industrial_subtype,certainty,evidence,
                    evidence_date,notes,reviewed_at FROM label_reviews
                    WHERE case_set_id=:s AND case_id=:id ORDER BY reviewed_at,id"""),
                {"s": set_id, "id": case_id},
            ).mappings()
        ]
    state = resolve_label(prior, case["review_slots"], None, None)
    pending = state["basis"] == "DISAGREEMENT_PENDING_ADJUDICATION"
    return {
        "case_id": case["id"],
        "case_set_id": str(set_id),
        "split": case["split"],
        "region_id": case["region_id"],
        "review_slots": case["review_slots"],
        "as_of": case["as_of"],
        "started_at": case["started_at"],
        "location": {
            "longitude": case["lon"],
            "latitude": case["lat"],
            "support_radius_m": round(radius, 1),
        },  # fmt: skip
        "observations": [dict(m) for m in members],
        "mapped_features": candidates[:12],
        "osm_snapshot": None
        if snapshot is None
        else {"osm_base_at": snapshot["osm_base_at"], "attribution": snapshot["attribution"]},
        "registry_records_within_5km": registry,
        "land_cover": land,
        "links": external_links(case["lon"], case["lat"], case["started_at"].date()),
        "blind": True,
        "reviews_recorded": len(prior),
        # Only an adjudicator sees earlier reviews (without reviewer names), to settle a
        # disagreement. Rule outputs, registry-derived labels and model scores are never shown.
        "adjudication": {"needed": True, "earlier_reviews": prior} if pending else None,
        "guidance": "Decide the likely heat source from independent evidence (imagery, registry "
        "records, official or company sources). Cite at least one link. Choose UNRESOLVED "
        "when the evidence does not support a decision. Do not guess. While reviewing, do not "
        "open the Observations page or its assessment panel: it shows automated assessments.",
        "labels": list(SOURCE_LABELS),
        "subtypes": list(SUBTYPES),
    }


def submit_review(settings: Settings, set_ref: str, payload: dict) -> dict:
    reviewer = str(payload.get("reviewer", "")).strip()
    label = payload.get("source_label")
    certainty = payload.get("certainty")
    evidence = payload.get("evidence") or []
    subtype = payload.get("industrial_subtype")
    notes = (payload.get("notes") or "").strip()[:2000]
    case_id = str(payload.get("case_id", ""))
    if not re.fullmatch(r"[\w .'-]{2,60}", reviewer):
        raise ValueError("reviewer name is required (2–60 letters)")
    if label not in SOURCE_LABELS or certainty not in {"HIGH", "MEDIUM", "LOW"}:
        raise ValueError("choose a source label and a certainty")
    if subtype is not None and (label != "INDUSTRIAL" or subtype not in SUBTYPES):
        raise ValueError("an industrial subtype applies only to INDUSTRIAL")
    if (
        not isinstance(evidence, list)
        or len(evidence) > 5
        or not all(isinstance(e, str) and URL.fullmatch(e) for e in evidence)
    ):
        raise ValueError("evidence must be up to five http(s) links")
    if label != "UNRESOLVED" and not evidence:
        raise ValueError("cite at least one evidence link, or choose UNRESOLVED")
    evidence_date = payload.get("evidence_date") or None
    with database_engine(settings) as engine, engine.begin() as conn:
        set_id = case_set_id(conn, set_ref)
        case = conn.execute(
            text("SELECT review_slots FROM label_cases WHERE case_set_id=:s AND id=:id FOR UPDATE"),
            {"s": set_id, "id": case_id},
        ).first()
        if case is None:
            raise LookupError("unknown case")
        existing = (
            conn.execute(
                text("""SELECT reviewer,role,source_label,evidence FROM label_reviews
                    WHERE case_set_id=:s AND case_id=:id ORDER BY reviewed_at,id"""),
                {"s": set_id, "id": case_id},
            )
            .mappings()
            .all()
        )
        if any(r["reviewer"].lower() == reviewer.lower() for r in existing):
            raise ValueError("this reviewer has already reviewed the case")
        reviewers = [r for r in existing if r["role"] == "REVIEWER"]
        state = resolve_label([dict(r) for r in existing], case[0], None, None)
        if state["basis"] == "DISAGREEMENT_PENDING_ADJUDICATION":
            role = "ADJUDICATOR"
        elif len(reviewers) < case[0]:
            role = "REVIEWER"
        else:
            raise ValueError("this case already has its reviews")
        review_id = uuid4()
        conn.execute(
            text("""
            INSERT INTO label_reviews (id,case_set_id,case_id,reviewer,role,source_label,
                industrial_subtype,certainty,evidence,evidence_date,notes,blind,reviewed_at)
            VALUES (:id,:s,:case,:reviewer,:role,:label,:subtype,:certainty,
                CAST(:evidence AS jsonb),:evidence_date,:notes,true,:now)
        """),
            {
                "id": review_id,
                "s": set_id,
                "case": case_id,
                "reviewer": reviewer,
                "role": role,
                "label": label,
                "subtype": subtype,
                "certainty": certainty,
                "evidence": json.dumps(evidence),
                "evidence_date": evidence_date,
                "notes": notes or None,
                "now": datetime.now(UTC),
            },
        )
    return {"review_id": str(review_id), "role": role, "case_id": case_id}


def cohen_kappa(pairs: list[tuple[str, str]]) -> float | None:
    if not pairs:
        return None
    n = len(pairs)
    observed = sum(a == b for a, b in pairs) / n
    cats = {x for p in pairs for x in p}
    expected = sum(
        (sum(a == c for a, _ in pairs) / n) * (sum(b == c for _, b in pairs) / n) for c in cats
    )
    return None if expected == 1 else round((observed - expected) / (1 - expected), 4)


def label_summary(settings: Settings, set_ref: str) -> dict:
    with database_engine(settings) as engine, engine.connect() as conn:
        set_id = case_set_id(conn, set_ref)
        labels = resolved_labels(conn, set_id)
        info = (
            conn.execute(
                text(
                    "SELECT name,case_count,manifest_sha256,created_at FROM case_sets WHERE id=:s"
                ),
                {"s": set_id},
            )
            .mappings()
            .one()
        )
        total = conn.execute(
            text("SELECT count(*) FROM label_reviews WHERE case_set_id=:s"), {"s": set_id}
        ).scalar_one()
        firsts = conn.execute(
            text("""
            SELECT case_id,array_agg(source_label ORDER BY reviewed_at,id) AS labels
            FROM label_reviews WHERE case_set_id=:s AND role='REVIEWER'
            GROUP BY case_id HAVING count(*) >= 2
        """),
            {"s": set_id},
        ).all()
    tiers = defaultdict(lambda: defaultdict(int))
    for item in labels.values():
        tiers[item["split"]][item["tier"] or "NONE"] += 1
    gold_test = defaultdict(int)
    for item in labels.values():
        if item["split"] == "TEST" and item["test_eligible"]:
            gold_test[item["label"]] += 1
    # Agreement on industrial vs not, over pairs where both reviewers decided.
    decided = [a for _, a in firsts if "UNRESOLVED" not in a[:2]]
    binary = [("IND" if a[0] == "INDUSTRIAL" else "NON", "IND" if a[1] == "INDUSTRIAL" else "NON")
              for a in decided]  # fmt: skip
    return {
        "case_set": dict(info) | {"id": str(set_id)},
        "label_policy": LABEL_POLICY,
        "tiers_by_split": {k: dict(v) for k, v in sorted(tiers.items())},
        "gold_test_labels": dict(gold_test),
        "reviews_total": total,
        "double_reviewed_cases": len(firsts),
        "binary_agreement_kappa": cohen_kappa(binary),
        "kappa_pairs": len(binary),
        "pending_adjudication": sum(
            1 for v in labels.values() if v["basis"] == "DISAGREEMENT_PENDING_ADJUDICATION"
        ),
    }


def models_list(settings: Settings) -> list[dict]:
    with database_engine(settings) as engine, engine.connect() as conn:
        rows = (
            conn.execute(
                text("""
            SELECT m.id,m.algorithm,m.status,m.label_policy,m.metrics,m.created_at,c.name
            FROM model_versions m JOIN case_sets c ON c.id=m.case_set_id
            ORDER BY m.created_at DESC LIMIT 20
        """)
            )
            .mappings()
            .all()
        )
    return [dict(r) | {"id": str(r["id"])} for r in rows]
