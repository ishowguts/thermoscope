"""As-of history features and transparent rules for source, behaviour and review priority.

These are heuristics with named conditions and uncalibrated default thresholds. They are not a
trained model and never produce a probability. Features use only observations acquired before
``as_of``; in OPERATIONAL mode, only inputs whose availability by ``as_of`` is on record.
"""

import hashlib
import json
import math
import statistics
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import text

from thermoscope.config import DataMode, Settings
from thermoscope.context import find_candidates, find_snapshot, snapshot_provider, support_radius_m
from thermoscope.database import database_engine
from thermoscope.landcover import PRODUCT_YEAR, PUBLISHED_ON, observation_landcover
from thermoscope.regions import NOAA20_PRODUCTS, Product

NRT_PRODUCT = Product.NOAA20.value
SP_PRODUCT = Product.NOAA20_SP.value

FEATURE_VERSION = "history-features-v3"  # v3: NOAA-20 SP/NRT stream, SP supersedes NRT
RULES_VERSION = "rules-v2"
SITE_RADIUS_M = 750.0  # same as the P03 link distance
EPISODE_HOURS = 24
WINDOWS = (7, 30, 90, 180)
BASELINE_WINDOW = 90
# Uncalibrated engineering defaults. No reviewed development set exists to calibrate them yet.
MIN_COVERAGE = 0.8
MIN_MATCHED_OVERPASSES = 5
ROBUST_Z_THRESHOLD = 3.5
MIN_LOG_SCALE = 0.1
Z_CAP = 50.0
RECURRENT_ACTIVE_DAYS = 5
BUILT_UP_SUPPORT = 0.25
CROPLAND_SUPPORT = 0.5
VEGETATION_SUPPORT = 0.5
THRESHOLDS = {
    "status": "UNCALIBRATED_DEFAULTS",
    "site_radius_m": SITE_RADIUS_M,
    "episode_hours": EPISODE_HOURS,
    "baseline_window_days": BASELINE_WINDOW,
    "min_coverage_fraction": MIN_COVERAGE,
    "min_matched_overpasses": MIN_MATCHED_OVERPASSES,
    "robust_z_threshold": ROBUST_Z_THRESHOLD,
    "min_log_scale": MIN_LOG_SCALE,
    "recurrent_active_days": RECURRENT_ACTIVE_DAYS,
    "built_up_support_fraction": BUILT_UP_SUPPORT,
    "cropland_support_fraction": CROPLAND_SUPPORT,
    "vegetation_support_fraction": VEGETATION_SUPPORT,
}
NOT_A_MODEL = (
    "Rule-based heuristic with uncalibrated thresholds. Not a trained model, not a probability "
    "and not a confirmed source or incident."
)


class Basis:
    RETROSPECTIVE = "RETROSPECTIVE"
    OPERATIONAL = "OPERATIONAL"


@dataclass(frozen=True)
class Detection:
    id: str
    acquired_at: datetime
    frp_mw: float | None
    satellite: str
    daynight: str
    product: str
    available_at: datetime | None  # earliest LIVE receipt; None means historically unknown


@dataclass(frozen=True)
class Coverage:
    start: date
    end: date
    received_at: datetime | None


def group_key(detection: Detection) -> str:
    return f"{detection.satellite}/{detection.daynight}"


def eligible(detections: list[Detection], as_of: datetime, basis: str) -> list[Detection]:
    """Nothing after as_of; operational mode also needs availability on record by as_of."""
    kept = [d for d in detections if d.acquired_at <= as_of]
    if basis == Basis.OPERATIONAL:
        kept = [d for d in kept if d.available_at is not None and d.available_at <= as_of]
    return kept


def covered_dates(runs: list[Coverage], as_of: datetime, basis: str) -> set[date]:
    days = set()
    for run in runs:
        if basis == Basis.OPERATIONAL and (run.received_at is None or run.received_at > as_of):
            continue
        day = run.start
        while day <= run.end:
            days.add(day)
            day += timedelta(days=1)
    return days


def product_family(product: str) -> tuple[str, ...]:
    """NOAA-20 NRT and standard-processing (SP) files are one sensor record; every other
    product stands alone, so an unrelated satellite can never add history or coverage."""
    return NOAA20_PRODUCTS if product in NOAA20_PRODUCTS else (product,)


def reconcile_stream(
    detections: list[Detection], run_rows, as_of: datetime | None = None, basis: str = ""
) -> tuple[list, list, int]:
    """Coverage from qualifying runs of the observation's product family, with SP taking
    precedence over NRT so one physical detection is never counted twice:
    - on a UTC day a qualifying SP run covers, that day's NRT detections are dropped;
    - otherwise an NRT detection is dropped only when an SP detection has the same acquisition
      time (the same overpass), so an incomplete SP day never removes other NRT data.
    An OPERATIONAL replay uses only SP runs and detections already on record by as_of.
    Returns (detections, runs, dropped)."""
    operational = basis == Basis.OPERATIONAL and as_of is not None
    sp_runs = [
        Coverage(*r[:3])
        for r in run_rows
        if r[3] == SP_PRODUCT and not (operational and (r[2] is None or r[2] > as_of))
    ]
    sp_days = covered_dates(sp_runs, None, "")
    sp_times = {
        d.acquired_at
        for d in detections
        if d.product == SP_PRODUCT
        and not (operational and (d.available_at is None or d.available_at > as_of))
    }
    kept = [
        d
        for d in detections
        if not (
            d.product == NRT_PRODUCT
            and (d.acquired_at.date() in sp_days or d.acquired_at in sp_times)
        )
    ]
    return kept, [Coverage(*r[:3]) for r in run_rows], len(detections) - len(kept)


def per_overpass_max(detections: list[Detection]) -> dict[tuple, float]:
    """One value per overpass and sensor group; FRP is never summed across overpasses."""
    maxima: dict[tuple, float] = {}
    for d in detections:
        if d.frp_mw is None:
            continue
        key = (d.acquired_at, group_key(d))
        maxima[key] = max(maxima.get(key, 0.0), d.frp_mw)
    return maxima


def robust_stats(values: list[float]) -> dict | None:
    if not values:
        return None
    logs = [math.log1p(v) for v in values]
    median = statistics.median(logs)
    mad = statistics.median(abs(v - median) for v in logs)
    ordered = sorted(values)

    def quantile(q):
        return ordered[min(len(ordered) - 1, max(0, math.ceil(q * len(ordered)) - 1))]

    return {
        "overpasses": len(values),
        "median_frp_mw": round(statistics.median(values), 3),
        "p10_frp_mw": round(quantile(0.1), 3),
        "p90_frp_mw": round(quantile(0.9), 3),
        "median_log1p": round(median, 5),
        "mad_log1p": round(mad, 5),
    }


def robust_z(value: float, stats: dict) -> dict:
    scale = 1.4826 * stats["mad_log1p"]
    floored = scale < MIN_LOG_SCALE
    z = (math.log1p(value) - stats["median_log1p"]) / max(scale, MIN_LOG_SCALE)
    capped = abs(z) > Z_CAP
    return {
        "robust_z": round(max(-Z_CAP, min(Z_CAP, z)), 3),
        "mad_zero": stats["mad_log1p"] == 0,
        "scale_floor_applied": floored,
        "capped": capped,
    }


def window_features(history: list[Detection], covered: set[date], start: datetime, days: int):
    window_start = start - timedelta(days=days)
    inside = [d for d in history if window_start <= d.acquired_at < start]
    dates = {(start - timedelta(days=k)).date() for k in range(1, days + 1)}
    last = max((d.acquired_at for d in inside), default=None)
    groups = {}
    for (_, key), value in sorted(per_overpass_max(inside).items()):
        groups.setdefault(key, []).append(value)
    return {
        "days": days,
        "window_start": window_start,
        "window_end": start,
        "covered_days": len(dates & covered),
        "coverage_fraction": round(len(dates & covered) / days, 3),
        "detections": len(inside),
        "overpasses": len({(d.acquired_at, d.satellite) for d in inside}),
        "active_days": len({d.acquired_at.date() for d in inside}),
        "last_detection_at": last,
        "days_since_last_detection": None
        if last is None
        else round((start - last) / timedelta(days=1), 2),
        "groups": {key: robust_stats(values) for key, values in groups.items()},
    }


def history_features(detections, runs, as_of: datetime, basis: str) -> dict:
    usable = eligible(detections, as_of, basis)
    episode_start = as_of - timedelta(hours=EPISODE_HOURS)
    current = [d for d in usable if d.acquired_at > episode_start]
    history = [d for d in usable if d.acquired_at <= episode_start]
    covered = covered_dates(runs, as_of, basis)
    current_groups = {}
    for (_, key), value in per_overpass_max(current).items():
        current_groups[key] = max(current_groups.get(key, 0.0), value)
    return {
        "version": FEATURE_VERSION,
        "as_of": as_of,
        "basis": basis,
        "episode_start": episode_start,
        "current": {
            "detections": len(current),
            "overpasses": len({(d.acquired_at, d.satellite) for d in current}),
            "max_frp_by_group": {k: round(v, 3) for k, v in sorted(current_groups.items())},
            "products": sorted({d.product for d in current}),
        },
        "windows": {str(w): window_features(history, covered, episode_start, w) for w in WINDOWS},
        "latest_input_acquired_at": max((d.acquired_at for d in usable), default=None),
        "excluded_after_as_of": sum(1 for d in detections if d.acquired_at > as_of),
        "excluded_unknown_availability": (
            sum(1 for d in detections if d.acquired_at <= as_of) - len(usable)
        ),
    }


def behaviour_rule(features: dict) -> dict:
    base = features["windows"][str(BASELINE_WINDOW)]
    current = features["current"]["max_frp_by_group"]
    reasons = []
    if not current:
        unavailable = features["basis"] == Basis.OPERATIONAL and (
            features["excluded_unknown_availability"] > 0
        )
        return {
            "label": "INSUFFICIENT_HISTORY",
            "rule": "B0_NO_CURRENT_FRP",
            "reasons": [
                "Operational replay cannot use this observation: its availability at the time "
                "is not on record (it arrived by file import or a later fetch)."
                if unavailable
                else "The current episode has no usable FRP value to compare."
            ],
        }
    if base["coverage_fraction"] < MIN_COVERAGE:
        return {
            "label": "INSUFFICIENT_HISTORY",
            "rule": "B1_LOW_COVERAGE",
            "reasons": [
                f"Only {base['covered_days']} of {BASELINE_WINDOW} earlier days were retrieved "
                "for this location; missing days are not evidence of no heat."
            ],
        }
    if base["active_days"] == 0:
        return {
            "label": "NEW_OR_TRANSIENT",
            "rule": "B2_NO_EARLIER_DETECTION",
            "reasons": [
                f"No earlier detection within {SITE_RADIUS_M:.0f} m in "
                f"{base['covered_days']} retrieved days. Non-detection can also mean cloud "
                "or no overpass."
            ],
        }
    comparisons = {}
    for key, value in sorted(current.items()):
        stats = base["groups"].get(key)
        if not stats or stats["overpasses"] < MIN_MATCHED_OVERPASSES:
            continue
        comparisons[key] = robust_z(value, stats) | {"current_max_frp_mw": value}
    if not comparisons:
        matched = {k: (base["groups"].get(k) or {}).get("overpasses", 0) for k in current}
        other = sorted(set(base["groups"]) - set(current))
        reasons.append(
            "Too few earlier overpasses in the same sensor/day-night group ("
            + ", ".join(f"{k}: {n}" for k, n in matched.items())
            + f"; need {MIN_MATCHED_OVERPASSES})."
        )
        if other:
            reasons.append(
                "History exists only for other groups ("
                + ", ".join(other)
                + "); different sensors or day/night are not compared."
            )
        return {"label": "INSUFFICIENT_HISTORY", "rule": "B3_UNMATCHED_HISTORY", "reasons": reasons}
    key, strongest = max(comparisons.items(), key=lambda item: abs(item[1]["robust_z"]))
    z = strongest["robust_z"]
    stats = base["groups"][key]
    detail = (
        f"Episode maximum within {SITE_RADIUS_M:.0f} m over the last {EPISODE_HOURS} h: "
        f"{strongest['current_max_frp_mw']} MW vs {stats['overpasses']} earlier {key} overpasses "
        f"(median {stats['median_frp_mw']} MW, 10–90% {stats['p10_frp_mw']}–"
        f"{stats['p90_frp_mw']} MW); robust z {z}."
    )
    flags = []
    skipped = sorted(set(current) - set(comparisons))
    if skipped:
        flags.append(
            "Not compared: "
            + ", ".join(
                f"{k} ({(base['groups'].get(k) or {}).get('overpasses', 0)} earlier overpasses)"
                for k in skipped
            )
            + f"; at least {MIN_MATCHED_OVERPASSES} are needed."
        )
    if strongest["mad_zero"]:
        flags.append("Earlier values were identical (MAD = 0); a minimum scale was used.")
    elif strongest["scale_floor_applied"]:
        flags.append("Earlier values varied very little; a minimum scale was used.")
    if strongest["capped"]:
        flags.append(f"The robust z was capped at ±{Z_CAP:.0f}.")
    label = (
        "ABNORMAL_RELATIVE_TO_BASELINE"
        if abs(z) >= ROBUST_Z_THRESHOLD
        else ("RECURRENT_WITHIN_BASELINE")
    )
    return {
        "label": label,
        "rule": "B4_ROBUST_Z",
        "direction": None if label != "ABNORMAL_RELATIVE_TO_BASELINE" else (
            "HIGHER" if z > 0 else "LOWER"
        ),
        "comparisons": comparisons,
        "reasons": [detail, *flags]
        + (
            ["Within the observed record means similar to earlier detections, not certified "
             "safe operation."]
            if label == "RECURRENT_WITHIN_BASELINE"
            else []
        ),
    }  # fmt: skip


def source_rule(context: dict, features: dict) -> dict:
    """Ordered heuristic; abstains with a reason rather than forcing a class."""
    mapped = context.get("candidates_in_support") or []
    candidates = [c for c in mapped if c.get("thermal_source_candidate", True)]
    land = context.get("land_cover_support")
    active = features["windows"][str(BASELINE_WINDOW)]["active_days"]
    conditions, reasons = [], []
    if not context.get("facility_context_available"):
        return {
            "label": "UNKNOWN",
            "reason_code": "CONTEXT_UNAVAILABLE_AS_OF",
            "heuristic_support": 0,
            "reasons": [context.get("facility_context_note", "No facility context.")],
        }
    if mapped and not candidates:
        return {
            "label": "UNKNOWN",
            "reason_code": "NON_THERMAL_POWER_CONTEXT",
            "heuristic_support": 0,
            "reasons": [
                "The mapped power feature is tagged as solar, wind or water power. It stays "
                "visible as context, but does not establish an industrial heat source. "
                "Recurrence alone does not identify what produced the heat."
            ],
        }
    types = sorted({c["facility_type"] for c in candidates})
    tags = {c["primary_tag"] for c in candidates}
    fractions = {x["class"]: x["fraction"] for x in (land or {}).get("fractions", [])}
    built = fractions.get("BUILT_UP", 0.0)
    crop = fractions.get("CROPLAND", 0.0)
    vegetation = sum(fractions.get(k, 0.0) for k in ("TREE_COVER", "SHRUBLAND", "GRASSLAND"))
    if candidates:
        conditions.append("MAPPED_INDUSTRIAL_IN_PIXEL_AREA")
        reasons.append(
            f"{len(candidates)} mapped industrial feature(s) in the pixel area "
            f"({', '.join(types)})."
        )
        if built >= BUILT_UP_SUPPORT:
            conditions.append("BUILT_UP_LAND_COVER")
            reasons.append(f"Built-up land cover {round(built * 100)}% in the pixel area.")
        if active >= RECURRENT_ACTIVE_DAYS:
            conditions.append("RECURRENT_AT_LOCATION")
            reasons.append(f"Detected on {active} earlier days within {SITE_RADIUS_M:.0f} m.")
        if len(conditions) >= 2:
            if "MINE" in types:
                subtype = "MINING_HEAT"
            elif "man_made=flare" in tags:
                subtype = "GAS_FLARE"
            elif "RECURRENT_AT_LOCATION" in conditions:
                subtype = "OTHER_PERSISTENT_HEAT"
            else:
                subtype = "UNRESOLVED"
            return {
                "label": "INDUSTRIAL",
                "subtype": subtype,
                "rule": "S1_MAPPED_INDUSTRY_WITH_SUPPORT",
                "conditions": conditions,
                "heuristic_support": len(conditions),
                "reasons": reasons,
            }
        reasons.append(
            "A mapped feature alone is not enough; land cover and history do not support it."
        )
        return {
            "label": "UNKNOWN",
            "reason_code": "WEAK_INDUSTRIAL_SUPPORT",
            "conditions": conditions,
            "heuristic_support": len(conditions),
            "reasons": reasons,
        }
    if land is None:
        return {
            "label": "UNKNOWN",
            "reason_code": "LAND_COVER_UNAVAILABLE",
            "heuristic_support": 0,
            "reasons": ["No mapped industry in the pixel area and no land cover to check."],
        }
    nearby = context.get("nearby_industrial", 0)
    if crop >= CROPLAND_SUPPORT and active < RECURRENT_ACTIVE_DAYS:
        if features["windows"][str(BASELINE_WINDOW)]["coverage_fraction"] < MIN_COVERAGE:
            return {
                "label": "UNKNOWN",
                "reason_code": "INSUFFICIENT_RECURRENCE_COVERAGE",
                "heuristic_support": 0,
                "reasons": [
                    "Cropland is mapped here, but too little history was retrieved to infer "
                    "that this source is not recurrent. Missing history is not absence of heat."
                ],
            }
        conditions = ["NO_MAPPED_INDUSTRY_IN_PIXEL_AREA", "CROPLAND_DOMINANT"]
        reasons = [
            "No mapped industrial feature in the pixel area.",
            f"Cropland {round(crop * 100)}% in the pixel area (WorldCover {PRODUCT_YEAR}).",
            f"Not recurrent at this location ({active} earlier active days).",
        ]
        if nearby:
            reasons.append(f"{nearby} mapped industrial feature(s) within 2 km, outside the area.")
        return {
            "label": "AGRICULTURAL_BURN",
            "rule": "S2_CROPLAND_NO_INDUSTRY",
            "conditions": conditions + ["NOT_RECURRENT"],
            "heuristic_support": 3,
            "reasons": reasons,
        }
    if vegetation >= VEGETATION_SUPPORT and crop < CROPLAND_SUPPORT:
        return {
            "label": "VEGETATION_FIRE",
            "rule": "S3_VEGETATION_NO_INDUSTRY",
            "conditions": ["NO_MAPPED_INDUSTRY_IN_PIXEL_AREA", "NATURAL_VEGETATION_DOMINANT"],
            "heuristic_support": 2,
            "reasons": [
                "No mapped industrial feature in the pixel area.",
                f"Tree, shrub and grass cover {round(vegetation * 100)}% (WorldCover "
                f"{PRODUCT_YEAR}).",
            ],
        }
    reasons = ["No rule matched cleanly."]
    if nearby:
        reasons.append(f"{nearby} mapped industrial feature(s) within 2 km but outside the area.")
    if crop:
        reasons.append(f"Cropland {round(crop * 100)}%, built-up {round(built * 100)}%.")
    if active >= RECURRENT_ACTIVE_DAYS:
        reasons.append(f"Recurrent at this location ({active} earlier active days).")
    return {
        "label": "UNKNOWN",
        "reason_code": "CONFLICTING_OR_MIXED_EVIDENCE",
        "heuristic_support": 0,
        "reasons": reasons,
    }


def priority_rule(source: dict, behaviour: dict) -> dict:
    """Ordered criteria; review priority, not accident probability or expected damage."""
    s, b = source["label"], behaviour["label"]
    higher = b == "ABNORMAL_RELATIVE_TO_BASELINE" and behaviour.get("direction") == "HIGHER"
    if s == "INDUSTRIAL" and higher:
        return {
            "label": "HIGH",
            "rule": "P1_INDUSTRIAL_ABOVE_BASELINE",
            "note": "POSSIBLE_ABNORMAL_INDUSTRIAL_EVENT — unusual FRP alone is not an incident.",
        }
    if s == "INDUSTRIAL" and b == "NEW_OR_TRANSIENT":
        return {
            "label": "HIGH",
            "rule": "P2_NEW_HEAT_AT_MAPPED_INDUSTRY",
            "note": "New detection at a mapped industrial feature; check recent imagery and "
            "operator or official records.",
        }
    if s == "UNKNOWN" and (higher or b == "NEW_OR_TRANSIENT"):
        return {
            "label": "REVIEW",
            "rule": "P3_UNRESOLVED_SOURCE_WITH_CHANGE",
            "note": "Source unresolved and activity has changed; look before dismissing it.",
        }
    if b == "INSUFFICIENT_HISTORY" and s in {"INDUSTRIAL", "UNKNOWN"}:
        return {
            "label": "MEDIUM",
            "rule": "P4_INCOMPLETE_EVIDENCE",
            "note": "History or context is incomplete; revisit when more data is retrieved.",
        }
    if s == "UNKNOWN":
        return {
            "label": "MEDIUM",
            "rule": "P5_UNRESOLVED_SOURCE",
            "note": "Source unresolved; activity is within its observed record.",
        }
    if s == "INDUSTRIAL":
        return {
            "label": "LOW",
            "rule": "P6_PERSISTENT_WITHIN_RECORD",
            "note": "Kept in the list: a persistent site is not suppressed or certified safe.",
        }
    return {
        "label": "LOW",
        "rule": "P7_NON_INDUSTRIAL_HEURISTIC",
        "note": "Outside the industrial review scope on current heuristics; still visible.",
    }


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()


def assess(detections, runs, context: dict, as_of: datetime, basis: str) -> dict:
    features = history_features(detections, runs, as_of, basis)
    behaviour = behaviour_rule(features)
    source = source_rule(context, features)
    priority = priority_rule(source, behaviour)
    snapshot = {"features": features, "context": context, "thresholds": THRESHOLDS}
    missing = []
    if features["excluded_unknown_availability"]:
        missing.append(
            f"{features['excluded_unknown_availability']} earlier observation(s) excluded: "
            "availability at that time is not on record."
        )
    if not context.get("facility_context_available"):
        missing.append("Facility context not available as of this time.")
    if context.get("land_cover_support") is None:
        missing.append("Land cover not available.")
    if basis == Basis.RETROSPECTIVE:
        missing.append(
            "Retrospective: uses everything acquired before this time, including data this "
            "application only retrieved later."
        )
    return {
        "as_of": as_of,
        "basis": basis,
        "feature_version": FEATURE_VERSION,
        "rules_version": RULES_VERSION,
        "method": "RULES",
        "not_a_model": NOT_A_MODEL,
        "source": source,
        "behaviour": behaviour,
        "priority": priority,
        "features": features,
        "context": context,
        "thresholds": THRESHOLDS,
        "missing_or_limited": missing,
        "feature_snapshot_sha256": digest(snapshot),
    }


# ---------------------------------------------------------------------------------------------
# Database loading


def load_inputs(conn, observation_id: str, mode: DataMode, as_of: datetime | None, basis: str):
    obs = (
        conn.execute(
            text("""
        SELECT o.id,o.acquired_at,o.product,ST_X(o.geom) AS lon,ST_Y(o.geom) AS lat,
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
    as_of = as_of or obs["acquired_at"]
    if as_of < obs["acquired_at"]:
        raise ValueError("as_of precedes the observation")
    point = {"lon": obs["lon"], "lat": obs["lat"]}
    family = product_family(obs["product"])
    rows = conn.execute(
        text("""
        SELECT o.id,o.acquired_at,(o.payload->>'frp_mw')::double precision,
            o.payload->>'satellite',o.payload->>'daynight',o.product,
            (SELECT min(r.received_at) FROM observation_receipts x
                JOIN ingestion_runs r ON r.id=x.run_id
                WHERE x.observation_id=o.id AND r.data_mode='LIVE'
                AND r.status IN ('SUCCEEDED','PARTIAL')) AS available_at
        FROM observations o
        WHERE ST_DWithin(o.geom,ST_SetSRID(ST_Point(:lon,:lat),4326),:degrees)
            AND ST_DWithin(o.geom::geography,ST_SetSRID(ST_Point(:lon,:lat),4326)::geography,:r)
            AND o.product = ANY(:family)
            AND o.acquired_at > :earliest
            AND EXISTS (SELECT 1 FROM observation_receipts x JOIN ingestion_runs r
                ON r.id=x.run_id WHERE x.observation_id=o.id AND r.data_mode=:mode
                AND r.status IN ('SUCCEEDED','PARTIAL'))
        ORDER BY o.acquired_at,o.id
    """),
        point
        | {
            "r": SITE_RADIUS_M,
            # Indexed planar pre-filter that always contains the geodesic circle.
            "degrees": SITE_RADIUS_M
            / (111_000.0 * math.cos(math.radians(min(abs(obs["lat"]), 85.0))))
            * 1.1,
            "mode": mode.value,
            "family": list(family),
            "earliest": as_of - timedelta(days=max(WINDOWS) + 2),
        },
    ).all()
    run_rows = conn.execute(
        text("""
        SELECT start_date,end_date,received_at,product FROM ingestion_runs
        WHERE data_mode=:mode AND product = ANY(:family) AND status='SUCCEEDED'
            AND rejected_rows=0
            AND ST_Covers(bounds,ST_Buffer(
                ST_SetSRID(ST_Point(:lon,:lat),4326)::geography,:radius)::geometry)
        ORDER BY start_date,id
    """),
        point | {"mode": mode.value, "family": list(family), "radius": SITE_RADIUS_M},
    ).all()
    detections, runs, superseded = reconcile_stream(
        [Detection(*row) for row in rows], run_rows, as_of, basis
    )
    radius, basis_note = support_radius_m(obs["scan_km"], obs["track_km"])
    snapshot = find_snapshot(
        conn,
        obs["lon"],
        obs["lat"],
        snapshot_provider(mode),
        received_by=as_of if basis == Basis.OPERATIONAL else None,
        radius=max(radius, 2000.0),
    )
    context = {
        "support_radius_m": round(radius, 1),
        "support_basis": basis_note,
        "facility_context_available": snapshot is not None,
    }
    if snapshot is None:
        context["facility_context_note"] = (
            "No OSM snapshot had been retrieved by this time."
            if basis == Basis.OPERATIONAL
            else "No OSM snapshot covers this location."
        )
    else:
        candidates, _ = find_candidates(conn, obs["lon"], obs["lat"], radius, snapshot["id"])
        inside = [c for c in candidates if c["relation"] == "INSIDE_SUPPORT"]
        context |= {
            "facility_snapshot_id": str(snapshot["id"]),
            "osm_base_at": snapshot["osm_base_at"],
            "osm_timing": "RETROSPECTIVE" if snapshot["osm_base_at"] > as_of else "PRIOR_STATE",
            "candidates_in_support": [
                {
                    k: c[k]
                    for k in (
                        "osm_type",
                        "osm_id",
                        "facility_type",
                        "primary_tag",
                        "distance_m",
                        "name",
                        "power_source",
                        "thermal_source_candidate",
                    )
                }
                for c in inside
            ],  # fmt: skip
            # Solar, wind and water power stay visible as candidates but are not counted as
            # nearby industry in the reasons (ADR-020).
            "nearby_industrial": sum(
                1
                for c in candidates
                if c["relation"] != "INSIDE_SUPPORT" and c.get("thermal_source_candidate", True)
            ),
        }
    land = None
    if date.fromisoformat(PUBLISHED_ON) <= as_of.date():
        summary = observation_landcover(conn, observation_id, obs["acquired_at"])
        if summary and summary["status"] == "OK":
            land = summary["support"]
    context["land_cover_support"] = land
    context["land_cover_map_year"] = PRODUCT_YEAR if land else None
    return {"observation": dict(obs), "as_of": as_of, "detections": detections, "runs": runs,
            "context": context,
            "stream": {"products": list(family), "nrt_superseded_by_sp": superseded}}  # fmt: skip


def observation_assessment(
    settings: Settings, observation_id: str, mode: DataMode, as_of: datetime | None, basis: str
) -> dict | None:
    with (
        database_engine(settings) as engine,
        engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn,
    ):
        inputs = load_inputs(conn, observation_id, mode, as_of, basis)
    if inputs is None:
        return None
    result = assess(inputs["detections"], inputs["runs"], inputs["context"], inputs["as_of"], basis)
    result["stream"] = inputs["stream"]
    result["observation_id"] = observation_id
    result["data_mode"] = mode.value
    result["subject"] = {
        "longitude": inputs["observation"]["lon"],
        "latitude": inputs["observation"]["lat"],
        "radius_m": SITE_RADIUS_M,
        "note": f"History is everything detected within {SITE_RADIUS_M:.0f} m of this pixel "
        "centre, independent of event grouping.",
    }
    return result


def observation_timeline(
    settings: Settings, observation_id: str, mode: DataMode, days: int, basis: str
) -> dict | None:
    with (
        database_engine(settings) as engine,
        engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn,
    ):
        inputs = load_inputs(conn, observation_id, mode, None, basis)
    if inputs is None:
        return None
    as_of = inputs["as_of"]
    usable = eligible(inputs["detections"], as_of, basis)
    covered = covered_dates(inputs["runs"], as_of, basis)
    series = []
    for k in range(days, -1, -1):
        day = (as_of - timedelta(days=k)).date()
        todays = [d for d in usable if d.acquired_at.date() == day]
        frps = [d.frp_mw for d in todays if d.frp_mw is not None]
        series.append(
            {
                "date": day,
                "retrieved": day in covered,
                "detections": len(todays),
                "day_detections": sum(1 for d in todays if d.daynight == "D"),
                "night_detections": sum(1 for d in todays if d.daynight == "N"),
                "max_frp_mw": max(frps) if frps else None,
            }
        )
    start = as_of - timedelta(days=days)
    in_range = [d for d in usable if d.acquired_at >= start]
    passes: dict[tuple, dict] = {}
    for d in in_range:
        item = passes.setdefault(
            (d.acquired_at, d.satellite, d.daynight),
            {
                "acquired_at": d.acquired_at,
                "satellite": d.satellite,
                "daynight": d.daynight,
                "group": group_key(d),
                "detections": 0,
                "max_frp_mw": None,
            },
        )
        item["detections"] += 1
        if d.frp_mw is not None:
            item["max_frp_mw"] = max(item["max_frp_mw"] or 0.0, d.frp_mw)
    return {
        "observation_id": observation_id,
        "as_of": as_of,
        "basis": basis,
        "radius_m": SITE_RADIUS_M,
        "episode_start": as_of - timedelta(hours=EPISODE_HOURS),
        "overpasses": [passes[k] for k in sorted(passes)],
        "days": series,
        "note": "Days not retrieved are unknown, not zero. A retrieved day without a detection "
        "can still hide heat under cloud or between overpasses.",
        "generated_at": datetime.now(UTC),
    }
