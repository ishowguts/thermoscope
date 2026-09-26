"""Deterministic events (bounded episodes) and recurring sites from stored observations.

Parameters are engineering defaults from the architecture (24 h gap, 750 m link), not physical
laws. A maximum diameter stops chain-linking across neighbouring facilities. Identities are
hashes of memberships, so a fixed input set and parameter version always gives the same result.
"""

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import text

from thermoscope.config import DataMode, Settings
from thermoscope.database import database_engine
from thermoscope.firms import IngestError
from thermoscope.regions import REGIONS, Bounds, Product

ALGORITHM_VERSION = "event-site-v1"
MAX_INPUT_OBSERVATIONS = 20_000
RECEIPT_FILTER = """
    EXISTS (SELECT 1 FROM observation_receipts x JOIN ingestion_runs r ON r.id=x.run_id
            WHERE x.observation_id=o.id AND r.data_mode=:mode
            AND r.status IN ('SUCCEEDED','PARTIAL'))
"""


@dataclass(frozen=True)
class Params:
    max_gap_hours: float = 24.0
    link_distance_m: float = 750.0
    max_diameter_m: float = 1500.0
    site_link_distance_m: float = 750.0
    site_max_diameter_m: float = 1500.0

    def sha256(self) -> str:
        body = {"version": ALGORITHM_VERSION} | asdict(self)
        return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class Point:
    id: str
    acquired_at: datetime
    frp_mw: float | None = None


class Distances:
    """Geodesic metres from PostGIS; pairs farther than the query limit count as infinite."""

    def __init__(self, pairs: dict[tuple[str, str], float]):
        self.pairs = {tuple(sorted(k)): v for k, v in pairs.items()}

    def get(self, a: str, b: str) -> float:
        return 0.0 if a == b else self.pairs.get((a, b) if a < b else (b, a), math.inf)

    def diameter(self, members: list[str]) -> float:
        return max(
            (self.get(a, b) for i, a in enumerate(members) for b in members[i + 1 :]),
            default=0.0,
        )


@dataclass
class Group:
    key: tuple
    members: list[str] = field(default_factory=list)
    last_at: datetime | None = None
    ambiguous: int = 0
    merged: bool = False


def build_events(points: list[Point], dist: Distances, params: Params):
    """Process observations in (time, id) order; return member lists and the merge count."""
    gap = timedelta(hours=params.max_gap_hours)
    groups: list[Group] = []
    merges = 0
    for point in sorted(points, key=lambda p: (p.acquired_at, p.id)):
        candidates = []
        for group in groups:
            if group.merged or point.acquired_at - group.last_at > gap:
                continue
            link = min(dist.get(point.id, m) for m in group.members)
            if link <= params.link_distance_m:
                fits = all(dist.get(point.id, m) <= params.max_diameter_m for m in group.members)
                candidates.append((link, group.key, group, fits))
        candidates.sort(key=lambda c: (c[0], c[1]))
        fitting = [c for c in candidates if c[3]]
        if not fitting:
            target = Group(key=(point.acquired_at, point.id))
            target.ambiguous += 1 if candidates else 0  # linked, but would exceed the diameter
            groups.append(target)
        elif len(fitting) == 1:
            target = fitting[0][2]
            target.ambiguous += 1 if len(candidates) > 1 else 0
        else:
            union = [m for c in fitting for m in c[2].members] + [point.id]
            if dist.diameter(union) <= params.max_diameter_m:
                target = min(fitting, key=lambda c: c[1])[2]
                for _, _, other, _ in fitting:
                    if other is not target:
                        target.members.extend(other.members)
                        target.ambiguous += other.ambiguous
                        other.merged = True
                merges += 1
            else:
                target = fitting[0][2]  # nearest; the other links are recorded, not merged
                target.ambiguous += 1
        target.members.append(point.id)
        target.last_at = point.acquired_at
    return [g for g in groups if not g.merged], merges


def build_sites(events: list[dict], dist: Distances, params: Params) -> list[dict]:
    """Group events by location regardless of time; anchor-based identity stays stable."""
    sites: list[dict] = []
    for event in sorted(events, key=lambda e: (e["started_at"], e["id"])):
        candidates = []
        for site in sites:
            link = min(dist.get(a, b) for a in event["members"] for b in site["members"])
            if link <= params.site_link_distance_m:
                fits = dist.diameter(site["members"] + event["members"]) <= (
                    params.site_max_diameter_m
                )
                candidates.append((link, site["anchor"], site, fits))
        candidates.sort(key=lambda c: (c[0], c[1]))
        fitting = [c for c in candidates if c[3]]
        if fitting:
            site = fitting[0][2]
            site["ambiguous"] += 1 if len(candidates) > 1 else 0
        else:
            site = {"anchor": event["members"][0], "members": [], "events": [], "ambiguous": 0}
            sites.append(site)
        site["members"].extend(event["members"])
        site["events"].append(event)
        event["site_anchor"] = site["anchor"]
    return sites


def membership_id(kind: str, params_sha: str, members: list[str]) -> str:
    body = {"kind": kind, "version": ALGORITHM_VERSION, "params": params_sha, "members": members}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def lineage(new: dict[str, set], old: dict[str, set]) -> list[tuple[str, str, str, int]]:
    """Relate each new event to earlier events that share observations."""
    links = [(n, o, len(new[n] & old[o])) for n in new for o in old if new[n] & old[o]]
    sources = {n: sum(1 for x, _, _ in links if x == n) for n in new}
    targets = {o: sum(1 for _, y, _ in links if y == o) for o in old}
    result = []
    for n, o, shared in sorted(links):
        if sources[n] > 1 and targets[o] > 1:
            relation = "CHANGED"
        elif sources[n] > 1:
            relation = "MERGED"
        elif targets[o] > 1:
            relation = "SPLIT"
        elif new[n] == old[o]:
            relation = "SAME"
        elif old[o] < new[n]:
            relation = "GREW"
        elif new[n] < old[o]:
            relation = "SHRANK"
        else:
            relation = "CHANGED"
        result.append((n, o, relation, shared))
    return result


def region_bounds(region_id: str) -> Bounds:
    for region in REGIONS:
        if region["id"] == region_id:
            return Bounds.parse(region["bbox"])
    raise IngestError("UNKNOWN_REGION")


def build_event_run(
    settings: Settings,
    region_id: str,
    mode: DataMode,
    *,
    product: Product = Product.NOAA20,
    params: Params | None = None,
    force: bool = False,
) -> dict:
    params = params or Params()
    params_sha = params.sha256()
    bounds = region_bounds(region_id)
    scope = bounds.model_dump() | {
        "mode": mode.value,
        "product": product.value,
        "region": region_id,
        "version": ALGORITHM_VERSION,
        "params_sha": params_sha,
    }
    with database_engine(settings) as engine, engine.begin() as conn:
        conn.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
            {"key": f"events:{region_id}:{mode.value}:{product.value}"},
        )
        rows = conn.execute(
            text(f"""
            SELECT o.id,o.acquired_at,(o.payload->>'frp_mw')::double precision AS frp
            FROM observations o
            WHERE o.product=:product AND o.geom && ST_MakeEnvelope(:west,:south,:east,:north,4326)
                AND {RECEIPT_FILTER}
            ORDER BY o.acquired_at,o.id
        """),
            scope,
        ).all()
        if len(rows) > MAX_INPUT_OBSERVATIONS:
            raise IngestError("EVENT_INPUT_LIMIT_EXCEEDED")
        points = [Point(r[0], r[1], r[2]) for r in rows]
        pairs = conn.execute(
            text(f"""
            WITH s AS (
                SELECT o.id,o.geom FROM observations o
                WHERE o.product=:product
                    AND o.geom && ST_MakeEnvelope(:west,:south,:east,:north,4326)
                    AND {RECEIPT_FILTER})
            SELECT a.id,b.id,ST_Distance(a.geom::geography,b.geom::geography)
            FROM s a JOIN s b ON a.id < b.id
                AND ST_DWithin(a.geom::geography,b.geom::geography,:limit)
        """),
            scope | {"limit": max(params.max_diameter_m, params.site_max_diameter_m)},
        ).all()
        dist = Distances({(a, b): float(d) for a, b, d in pairs})
        input_sha = hashlib.sha256("\n".join(sorted(p.id for p in points)).encode()).hexdigest()
        previous = (
            conn.execute(
                text("""
            SELECT id,input_sha256,latest_input_acquired_at FROM event_runs
            WHERE region_id=:region AND data_mode=:mode AND product=:product
                AND algorithm_version=:version AND params_sha256=:params_sha
            ORDER BY created_at DESC,id LIMIT 1
        """),
                scope,
            )
            .mappings()
            .first()
        )
        if previous and previous["input_sha256"] == input_sha and not force:
            return {"status": "UNCHANGED", "run_id": str(previous["id"])}

        groups, merges = build_events(points, dist, params)
        by_id = {p.id: p for p in points}
        events = []
        for group in groups:
            members = sorted(group.members, key=lambda m: (by_id[m].acquired_at, m))
            frps = [by_id[m].frp_mw for m in members if by_id[m].frp_mw is not None]
            events.append(
                {
                    "id": membership_id("event", params_sha, sorted(members)),
                    "members": members,
                    "started_at": by_id[members[0]].acquired_at,
                    "ended_at": by_id[members[-1]].acquired_at,
                    "overpasses": len({by_id[m].acquired_at for m in members}),
                    # FRP is never summed across overpasses; only the maximum is kept.
                    "max_frp": max(frps) if frps else None,
                    "diameter": dist.diameter(members),
                    "ambiguous": group.ambiguous,
                }
            )
        sites = build_sites(events, dist, params)
        for site in sites:
            site["id"] = membership_id("site", params_sha, [site["anchor"]])
            for event in site["events"]:
                event["site_id"] = site["id"]

        late, earliest_late, previous_events = 0, None, {}
        if previous:
            old_rows = conn.execute(
                text("SELECT event_id,observation_id FROM event_observations WHERE run_id=:run"),
                {"run": previous["id"]},
            ).all()
            for event_id, observation_id in old_rows:
                previous_events.setdefault(event_id, set()).add(observation_id)
            seen = set().union(*previous_events.values()) if previous_events else set()
            cutoff = previous["latest_input_acquired_at"]
            late_points = [
                p for p in points if p.id not in seen and cutoff and p.acquired_at < cutoff
            ]
            late = len(late_points)
            earliest_late = min((p.acquired_at for p in late_points), default=None)

        run_id = uuid4()
        conn.execute(
            text("""
            INSERT INTO event_runs (id,algorithm_version,params,params_sha256,data_mode,product,
                region_id,bounds,input_count,input_sha256,latest_input_acquired_at,
                previous_run_id,late_arrivals,earliest_late_arrival_at,merges_in_run,
                ambiguous_links,event_count,site_count,created_at)
            VALUES (:id,:version,CAST(:params AS jsonb),:params_sha,:mode,:product,:region,
                ST_MakeEnvelope(:west,:south,:east,:north,4326),:count,:input_sha,:latest,
                :previous,:late,:earliest_late,:merges,:ambiguous,:events,:sites,:created)
        """),
            scope
            | {
                "id": run_id,
                "params": json.dumps(asdict(params), sort_keys=True),
                "count": len(points),
                "input_sha": input_sha,
                "latest": points[-1].acquired_at if points else None,
                "previous": previous["id"] if previous else None,
                "late": late,
                "earliest_late": earliest_late,
                "merges": merges,
                "ambiguous": sum(e["ambiguous"] for e in events)
                + sum(s["ambiguous"] for s in sites),
                "events": len(events),
                "sites": len(sites),
                "created": datetime.now(UTC),
            },
        )
        hull = """ST_ConvexHull(ST_Collect(ARRAY(
            SELECT geom FROM observations WHERE id = ANY(:members))))"""
        for site in sites:
            times = [e["started_at"] for e in site["events"]] + [
                e["ended_at"] for e in site["events"]
            ]
            conn.execute(
                text(f"""
                INSERT INTO sites (run_id,id,first_seen_at,last_seen_at,event_count,
                    observation_count,diameter_m,geom)
                VALUES (:run,:id,:first,:last,:events,:count,:diameter,{hull})
            """),
                {
                    "run": run_id,
                    "id": site["id"],
                    "first": min(times),
                    "last": max(times),
                    "events": len(site["events"]),
                    "count": len(site["members"]),
                    "diameter": dist.diameter(site["members"]),
                    "members": site["members"],
                },
            )
        for event in events:
            conn.execute(
                text(f"""
                INSERT INTO events (run_id,id,site_id,started_at,ended_at,observation_count,
                    overpass_count,max_frp_mw,diameter_m,ambiguous_links,geom)
                VALUES (:run,:id,:site,:start,:end,:count,:overpasses,:frp,:diameter,
                    :ambiguous,{hull})
            """),
                {
                    "run": run_id,
                    "id": event["id"],
                    "site": event["site_id"],
                    "start": event["started_at"],
                    "end": event["ended_at"],
                    "count": len(event["members"]),
                    "overpasses": event["overpasses"],
                    "frp": event["max_frp"],
                    "diameter": event["diameter"],
                    "ambiguous": event["ambiguous"],
                    "members": event["members"],
                },
            )
            for member in event["members"]:
                conn.execute(
                    text("""
                    INSERT INTO event_observations (run_id,event_id,observation_id)
                    VALUES (:run,:event,:observation)
                """),
                    {"run": run_id, "event": event["id"], "observation": member},
                )
        links = lineage({e["id"]: set(e["members"]) for e in events}, previous_events)
        for new_id, old_id, relation, shared in links:
            conn.execute(
                text("""
                INSERT INTO event_lineage (run_id,event_id,previous_run_id,previous_event_id,
                    relation,shared_observations)
                VALUES (:run,:event,:previous_run,:previous_event,:relation,:shared)
            """),
                {
                    "run": run_id,
                    "event": new_id,
                    "previous_run": previous["id"],
                    "previous_event": old_id,
                    "relation": relation,
                    "shared": shared,
                },
            )
    return {
        "status": "SUCCEEDED",
        "run_id": str(run_id),
        "algorithm_version": ALGORITHM_VERSION,
        "params_sha256": params_sha,
        "input_count": len(points),
        "event_count": len(events),
        "site_count": len(sites),
        "merges_in_run": merges,
        "late_arrivals": late,
        "lineage": {r: sum(1 for x in links if x[2] == r) for r in sorted({x[2] for x in links})},
    }


LATEST_RUNS = """
    SELECT DISTINCT ON (region_id) id,region_id,created_at,params,input_count,late_arrivals
    FROM event_runs
    WHERE data_mode=:mode AND product=:product AND algorithm_version=:version
        AND bounds && ST_MakeEnvelope(:west,:south,:east,:north,4326)
    ORDER BY region_id,created_at DESC,id
"""


def list_events(settings, bounds: Bounds, start, end, mode: DataMode, product: Product, limit):
    params = bounds.model_dump() | {
        "mode": mode.value,
        "product": product.value,
        "version": ALGORITHM_VERSION,
        "start": datetime.combine(start, datetime.min.time(), UTC),
        "end": datetime.combine(end + timedelta(days=1), datetime.min.time(), UTC),
        "limit": limit + 1,
    }
    with (
        database_engine(settings) as engine,
        engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn,
    ):
        runs = conn.execute(text(LATEST_RUNS), params).mappings().all()
        rows = []
        if runs:
            rows = (
                conn.execute(
                    text("""
                SELECT e.*,ST_AsGeoJSON(e.geom,6) AS geometry,s.event_count AS site_event_count,
                    s.first_seen_at AS site_first_seen_at
                FROM events e JOIN sites s ON s.run_id=e.run_id AND s.id=e.site_id
                WHERE e.run_id = ANY(:runs)
                    AND e.geom && ST_MakeEnvelope(:west,:south,:east,:north,4326)
                    AND e.started_at < :end AND e.ended_at >= :start
                ORDER BY e.started_at DESC,e.id LIMIT :limit
            """),
                    params | {"runs": [r["id"] for r in runs]},
                )
                .mappings()
                .all()
            )
    return {
        "type": "FeatureCollection",
        "features": [event_feature(row) for row in rows[:limit]],
        "meta": {
            "data_mode": mode.value,
            "algorithm_version": ALGORITHM_VERSION,
            "runs": [
                {
                    "id": str(r["id"]),
                    "region_id": r["region_id"],
                    "created_at": r["created_at"],
                    "params": r["params"],
                    "input_count": r["input_count"],
                    "late_arrivals": r["late_arrivals"],
                }
                for r in runs
            ],
            "truncated": len(rows) > limit,
            "classification_status": "NOT_IMPLEMENTED",
            "note": "Events group observations by time and distance; they are not confirmed "
            "fires or incidents.",
        },
    }


def event_feature(row) -> dict:
    return {
        "type": "Feature",
        "id": row["id"],
        "geometry": json.loads(row["geometry"]),
        "properties": {
            "run_id": str(row["run_id"]),
            "site_id": row["site_id"],
            "started_at": row["started_at"],
            "ended_at": row["ended_at"],
            "observation_count": row["observation_count"],
            "overpass_count": row["overpass_count"],
            "max_frp_mw": row["max_frp_mw"],
            "diameter_m": round(row["diameter_m"], 1),
            "ambiguous_links": row["ambiguous_links"],
            "site_event_count": row["site_event_count"],
            "site_first_seen_at": row["site_first_seen_at"],
        },
    }


def observation_event(conn, observation_id: str, mode: DataMode) -> dict | None:
    row = (
        conn.execute(
            text("""
        SELECT e.id,e.run_id,e.site_id,e.started_at,e.ended_at,e.observation_count,
            e.overpass_count,e.max_frp_mw,e.ambiguous_links,s.event_count AS site_event_count,
            s.observation_count AS site_observation_count,s.first_seen_at,s.last_seen_at,
            r.created_at AS run_created_at
        FROM event_observations x
        JOIN event_runs r ON r.id=x.run_id
        JOIN events e ON e.run_id=x.run_id AND e.id=x.event_id
        JOIN sites s ON s.run_id=e.run_id AND s.id=e.site_id
        WHERE x.observation_id=:id AND r.data_mode=:mode AND r.algorithm_version=:version
        ORDER BY r.created_at DESC,r.id LIMIT 1
    """),
            {"id": observation_id, "mode": mode.value, "version": ALGORITHM_VERSION},
        )
        .mappings()
        .first()
    )
    if row is None:
        return None
    return {
        "event_id": row["id"],
        "run_id": str(row["run_id"]),
        "run_created_at": row["run_created_at"],
        "algorithm_version": ALGORITHM_VERSION,
        "started_at": row["started_at"],
        "ended_at": row["ended_at"],
        "observation_count": row["observation_count"],
        "overpass_count": row["overpass_count"],
        "max_frp_mw": row["max_frp_mw"],
        "ambiguous_links": row["ambiguous_links"],
        "site": {
            "site_id": row["site_id"],
            "event_count": row["site_event_count"],
            "observation_count": row["site_observation_count"],
            "first_seen_at": row["first_seen_at"],
            "last_seen_at": row["last_seen_at"],
        },
    }


def event_detail(settings: Settings, event_id: str, mode: DataMode) -> dict | None:
    with (
        database_engine(settings) as engine,
        engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn,
    ):
        row = (
            conn.execute(
                text("""
            SELECT e.*,ST_AsGeoJSON(e.geom,6) AS geometry,s.event_count AS site_event_count,
                s.first_seen_at AS site_first_seen_at
            FROM events e JOIN event_runs r ON r.id=e.run_id
            JOIN sites s ON s.run_id=e.run_id AND s.id=e.site_id
            WHERE e.id=:id AND r.data_mode=:mode AND r.algorithm_version=:version
            ORDER BY r.created_at DESC,r.id LIMIT 1
        """),
                {"id": event_id, "mode": mode.value, "version": ALGORITHM_VERSION},
            )
            .mappings()
            .first()
        )
        if row is None:
            return None
        members = (
            conn.execute(
                text("""
            SELECT o.id,o.acquired_at,ST_X(o.geom) AS lon,ST_Y(o.geom) AS lat,
                (o.payload->>'frp_mw')::double precision AS frp_mw,
                o.payload->>'source_confidence' AS source_confidence
            FROM event_observations x JOIN observations o ON o.id=x.observation_id
            WHERE x.run_id=:run AND x.event_id=:id ORDER BY o.acquired_at,o.id
        """),
                {"run": row["run_id"], "id": event_id},
            )
            .mappings()
            .all()
        )
        links = (
            conn.execute(
                text("""
            SELECT previous_run_id,previous_event_id,relation,shared_observations
            FROM event_lineage WHERE run_id=:run AND event_id=:id
            ORDER BY previous_event_id
        """),
                {"run": row["run_id"], "id": event_id},
            )
            .mappings()
            .all()
        )
    feature = event_feature(row)
    feature["properties"]["observations"] = [dict(m) for m in members]
    feature["properties"]["lineage"] = [
        dict(link) | {"previous_run_id": str(link["previous_run_id"])} for link in links
    ]
    return feature
