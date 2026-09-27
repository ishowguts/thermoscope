"""P05 structured source classifier: case features, baselines, XGBoost, calibration, evaluation.

Nothing here certifies accuracy by itself. Test metrics count only when the TEST split has
reviewed (GOLD, double-reviewed or adjudicated) labels; otherwise the run is recorded as
INSUFFICIENT_LABELS or, when weak labels are used on purpose, DRY_RUN_NOT_EVIDENCE.
Artifacts are JSON (no pickle). Raw coordinates, IDs, names, dates and NASA's type are not
model inputs.
"""

import csv
import hashlib
import json
import statistics
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import numpy as np
from sqlalchemy import text

from thermoscope.assessment import (
    Basis,
    covered_dates,
    history_features,
    load_inputs,
    per_overpass_max,
    source_rule,
)
from thermoscope.config import DataMode, Settings
from thermoscope.context import find_candidates, find_snapshot, support_radius_m
from thermoscope.database import batch_engine, database_engine
from thermoscope.labels import (
    FEATURE_VERSION,
    LABEL_POLICY,
    REGISTRY_MATCH_M,
    case_set_id,
    registry_matches,
    resolved_labels,
)
from thermoscope.landcover import observation_landcover

MODEL_VERSION = "xgb-source-binary-v1"
DISTANCE_CAP_M = 5000.0
EPISODE = [
    "obs_count", "overpass_count", "duration_h", "frp_max", "frp_overpass_median",
    "bt_i4_median", "bt_i5_median", "bt_diff_median", "night_fraction", "high_conf_fraction",
    "low_conf_fraction", "scan_median", "track_median",
]  # fmt: skip
HISTORY = [
    "active_days_30", "active_days_90", "active_days_180", "overpasses_90", "coverage_90",
    "coverage_180", "days_since_last", "history_frp_median_90", "history_night_fraction_90",
]  # fmt: skip
OSM = [
    "osm_covered", "n_industrial_in_support", "nearest_industrial_m", "n_industrial_2km",
    "has_power", "has_refinery", "has_mine", "has_petrochem_steel_lng", "has_flare_tag",
    "has_chimney_tag", "has_kiln_tag",
]  # fmt: skip
LANDCOVER = [
    "lc_valid", "lc_built", "lc_crop", "lc_tree", "lc_shrub", "lc_grass", "lc_bare",
    "lc_water", "lc_wetland", "lc_built_1km", "lc_crop_1km", "lc_tree_1km",
]  # fmt: skip
FEATURES = EPISODE + HISTORY + OSM + LANDCOVER
FEATURE_SETS = {
    "thermal_history": EPISODE + HISTORY,
    "full": FEATURES,
    "full_minus_history": EPISODE + OSM + LANDCOVER,
    "full_minus_osm": EPISODE + HISTORY + LANDCOVER,
    "full_minus_landcover": EPISODE + HISTORY + OSM,
}
XGB_PARAMS = {
    "n_estimators": 300,
    "max_depth": 3,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 2,
    "reg_lambda": 1.0,
    "tree_method": "hist",
    "random_state": 7,
    "n_jobs": 1,
}
TARGET_RISK = 0.10
MIN_COVERAGE = 0.5
MIN_TEST_PER_CLASS_REPORT = 10
MIN_TEST_PER_CLASS_PROMOTE = 30
MIN_TRAIN_PER_CLASS = 20
BOOTSTRAP = 1000
NON_INDUSTRIAL = {"VEGETATION_FIRE", "AGRICULTURAL_BURN", "OTHER"}


def median(values):
    values = [v for v in values if v is not None]
    return float(statistics.median(values)) if values else None


# ---------------------------------------------------------------------------------------------
# Features


def episode_features(members: list[dict]) -> dict:
    times = [m["acquired_at"] for m in members]
    passes = defaultdict(float)
    for m in members:
        if m["frp_mw"] is not None:
            key = (m["acquired_at"], m["satellite"])
            passes[key] = max(passes[key], m["frp_mw"])
    n = len(members)
    return {
        "obs_count": n,
        "overpass_count": len({(m["acquired_at"], m["satellite"]) for m in members}),
        "duration_h": (max(times) - min(times)) / timedelta(hours=1),
        "frp_max": max(passes.values()) if passes else None,
        "frp_overpass_median": median(list(passes.values())),
        "bt_i4_median": median([m["i4"] for m in members]),
        "bt_i5_median": median([m["i5"] for m in members]),
        "bt_diff_median": median(
            [m["i4"] - m["i5"] for m in members if m["i4"] is not None and m["i5"] is not None]
        ),
        "night_fraction": sum(m["daynight"] == "N" for m in members) / n,
        "high_conf_fraction": sum(m["confidence"] == "h" for m in members) / n,
        "low_conf_fraction": sum(m["confidence"] == "l" for m in members) / n,
        "scan_median": median([m["scan"] for m in members]),
        "track_median": median([m["track"] for m in members]),
    }


def prior_history(detections, runs, started_at) -> dict:
    """Only detections strictly before the episode starts; coverage from retrieved days."""
    before = [d for d in detections if d.acquired_at < started_at]
    covered = covered_dates(runs, started_at, Basis.RETROSPECTIVE)

    def window(days):
        start = started_at - timedelta(days=days)
        inside = [d for d in before if d.acquired_at >= start]
        dates = {(started_at - timedelta(days=k)).date() for k in range(1, days + 1)}
        return inside, len(dates & covered) / days

    w30, _ = window(30)
    w90, cov90 = window(90)
    w180, cov180 = window(180)
    last = max((d.acquired_at for d in before), default=None)
    frp90 = list(per_overpass_max(w90).values())
    return {
        "active_days_30": len({d.acquired_at.date() for d in w30}),
        "active_days_90": len({d.acquired_at.date() for d in w90}),
        "active_days_180": len({d.acquired_at.date() for d in w180}),
        "overpasses_90": len({(d.acquired_at, d.satellite) for d in w90}),
        "coverage_90": round(cov90, 4),
        "coverage_180": round(cov180, 4),
        "days_since_last": None if last is None else (started_at - last) / timedelta(days=1),
        "history_frp_median_90": median(frp90),
        "history_night_fraction_90": (
            sum(d.daynight == "N" for d in w90) / len(w90) if w90 else None
        ),
    }


def osm_features(candidates: list[dict], covered: bool) -> dict:
    inside = [c for c in candidates if c["relation"] == "INSIDE_SUPPORT"]
    types = {c["facility_type"] for c in inside}
    tags = {c["primary_tag"] for c in inside}
    return {
        "osm_covered": int(covered),
        "n_industrial_in_support": len(inside),
        "nearest_industrial_m": min([c["distance_m"] for c in candidates] + [DISTANCE_CAP_M]),
        "n_industrial_2km": len(candidates),
        "has_power": int("POWER" in types),
        "has_refinery": int("REFINERY" in types),
        "has_mine": int("MINE" in types),
        "has_petrochem_steel_lng": int(bool(types & {"PETROCHEMICAL", "STEEL", "LNG"})),
        "has_flare_tag": int("man_made=flare" in tags),
        "has_chimney_tag": int("man_made=chimney" in tags),
        "has_kiln_tag": int("man_made=kiln" in tags),
    }


def landcover_features(land: dict | None) -> dict:
    if land is None:
        return {k: None for k in LANDCOVER}
    s = land["support"]
    c = land["context"]

    def fraction(summary, *classes):
        items = summary["fractions"]
        lookup = {x["class"]: x["fraction"] for x in items} if isinstance(items, list) else items
        return sum(lookup.get(k, 0.0) for k in classes)

    return {
        "lc_valid": s["valid_fraction"],
        "lc_built": fraction(s, "BUILT_UP"),
        "lc_crop": fraction(s, "CROPLAND"),
        "lc_tree": fraction(s, "TREE_COVER"),
        "lc_shrub": fraction(s, "SHRUBLAND"),
        "lc_grass": fraction(s, "GRASSLAND"),
        "lc_bare": fraction(s, "BARE_SPARSE_VEGETATION"),
        "lc_water": fraction(s, "PERMANENT_WATER"),
        "lc_wetland": fraction(s, "HERBACEOUS_WETLAND", "MANGROVES"),
        "lc_built_1km": fraction(c, "BUILT_UP"),
        "lc_crop_1km": fraction(c, "CROPLAND"),
        "lc_tree_1km": fraction(c, "TREE_COVER"),
    }


def compute_case_features(settings: Settings, set_ref: str) -> dict:
    written = weak = silver = 0
    with batch_engine(settings) as engine, engine.begin() as conn:
        set_id = case_set_id(conn, set_ref)
        mode = DataMode(
            conn.execute(
                text("SELECT data_mode FROM case_sets WHERE id=:s"), {"s": set_id}
            ).scalar_one()
        )
        cases = (
            conn.execute(
                text("""
            SELECT c.*,ST_X(c.geom) AS lon,ST_Y(c.geom) AS lat FROM label_cases c
            WHERE c.case_set_id=:s ORDER BY c.review_rank
        """),
                {"s": set_id},
            )
            .mappings()
            .all()
        )
        for case in cases:
            members = [
                dict(m)
                for m in conn.execute(
                    text("""
                SELECT o.id,o.acquired_at,(o.payload->>'frp_mw')::double precision AS frp_mw,
                    o.payload->>'satellite' AS satellite,o.payload->>'daynight' AS daynight,
                    o.payload->>'source_confidence' AS confidence,
                    (o.payload->>'brightness_i4_k')::double precision AS i4,
                    (o.payload->>'brightness_i5_k')::double precision AS i5,
                    (o.payload->>'scan_km')::double precision AS scan,
                    (o.payload->>'track_km')::double precision AS track,
                    (o.payload->>'nasa_type')::integer AS nasa_type
                FROM event_observations x JOIN observations o ON o.id=x.observation_id
                WHERE x.run_id=:run AND x.event_id=:event ORDER BY o.acquired_at,o.id
            """),
                    {"run": case["event_run_id"], "event": case["event_id"]},
                ).mappings()
            ]
            rep = next(m for m in members if m["id"] == case["representative_observation_id"])
            inputs = load_inputs(conn, rep["id"], mode, case["as_of"], Basis.RETROSPECTIVE)
            radius, _ = support_radius_m(rep["scan"], rep["track"])
            snapshot = find_snapshot(conn, case["lon"], case["lat"], "OSM_OVERPASS")
            candidates = []
            if snapshot:
                candidates, _ = find_candidates(
                    conn, case["lon"], case["lat"], radius, snapshot["id"]
                )
            land = observation_landcover(conn, rep["id"], rep["acquired_at"])
            features = (
                episode_features(members)
                | prior_history(inputs["detections"], inputs["runs"], case["started_at"])
                | osm_features(candidates, snapshot is not None)
                | landcover_features(land)
            )
            rule = source_rule(
                inputs["context"],
                history_features(
                    inputs["detections"], inputs["runs"], case["as_of"], Basis.RETROSPECTIVE
                ),
            )
            weak_label = rule["label"] if rule["label"] != "UNKNOWN" else None
            matches = [
                m
                for m in registry_matches(conn, case["lon"], case["lat"], REGISTRY_MATCH_M)
                if m["category"] == "THERMAL_POWER_PLANT"
            ]
            silver_label = "INDUSTRIAL" if matches else None
            types = [m["nasa_type"] for m in members if m["nasa_type"] is not None]
            nasa_type = max(set(types), key=types.count) if types else None
            body = json.dumps(features, sort_keys=True, default=float)
            conn.execute(
                text("""
                INSERT INTO case_features (case_set_id,case_id,feature_version,features,
                    weak_label,weak_rule,silver_label,silver_evidence,nasa_type_majority,
                    sha256,computed_at)
                VALUES (:s,:case,:version,CAST(:features AS jsonb),:weak,:rule,:silver,
                    CAST(:evidence AS jsonb),:nasa,:sha,:now)
                ON CONFLICT (case_set_id,case_id,feature_version) DO UPDATE SET
                    features=EXCLUDED.features,weak_label=EXCLUDED.weak_label,
                    weak_rule=EXCLUDED.weak_rule,silver_label=EXCLUDED.silver_label,
                    silver_evidence=EXCLUDED.silver_evidence,
                    nasa_type_majority=EXCLUDED.nasa_type_majority,sha256=EXCLUDED.sha256,
                    computed_at=EXCLUDED.computed_at
            """),
                {
                    "s": set_id,
                    "case": case["id"],
                    "version": FEATURE_VERSION,
                    "features": body,
                    "weak": weak_label,
                    "rule": rule.get("rule") or rule.get("reason_code"),
                    "silver": silver_label,
                    "evidence": json.dumps(matches[:3]) if matches else None,
                    "nasa": nasa_type,
                    "sha": hashlib.sha256(body.encode()).hexdigest(),
                    "now": datetime.now(UTC),
                },
            )
            written += 1
            weak += weak_label is not None
            silver += silver_label is not None
    return {"case_set_id": str(set_id), "feature_version": FEATURE_VERSION, "cases": written,
            "weak_labels": weak, "silver_labels": silver}  # fmt: skip


# ---------------------------------------------------------------------------------------------
# Metrics


def binary_target(label: str | None) -> int | None:
    if label == "INDUSTRIAL":
        return 1
    if label in NON_INDUSTRIAL:
        return 0
    return None


def classification_metrics(y, pred) -> dict:
    y, pred = np.asarray(y), np.asarray(pred)
    out = {"support": {"INDUSTRIAL": int((y == 1).sum()), "NON_INDUSTRIAL": int((y == 0).sum())}}
    matrix = [[int(((y == a) & (pred == b)).sum()) for b in (1, 0)] for a in (1, 0)]
    out["confusion_matrix"] = {
        "rows_true": ["INDUSTRIAL", "NON_INDUSTRIAL"],
        "cols_pred": ["INDUSTRIAL", "NON_INDUSTRIAL"],
        "counts": matrix,
    }
    f1s = []
    for name, cls in (("INDUSTRIAL", 1), ("NON_INDUSTRIAL", 0)):
        tp = int(((pred == cls) & (y == cls)).sum())
        fp = int(((pred == cls) & (y != cls)).sum())
        fn = int(((pred != cls) & (y == cls)).sum())
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        out[name] = {"precision": round(precision, 4), "recall": round(recall, 4),
                     "f1": round(f1, 4)}  # fmt: skip
        f1s.append(f1)
    out["macro_f1"] = round(float(np.mean(f1s)), 4)
    out["accuracy"] = round(float((y == pred).mean()), 4) if len(y) else None
    return out


def macro_f1(y, pred) -> float:
    return classification_metrics(y, pred)["macro_f1"]


def reliability(y, p, bins=10) -> list[dict]:
    y, p = np.asarray(y), np.asarray(p)
    out = []
    for i in range(bins):
        lo, hi = i / bins, (i + 1) / bins
        mask = (p >= lo) & ((p < hi) if i < bins - 1 else (p <= hi))
        if mask.any():
            out.append({"bin": f"{lo:.1f}-{hi:.1f}", "count": int(mask.sum()),
                        "mean_predicted": round(float(p[mask].mean()), 4),
                        "observed_industrial": round(float(y[mask].mean()), 4)})  # fmt: skip
    return out


def choose_abstention(y_val, p_val) -> dict:
    """Smallest confidence cut whose validation risk ≤ target at ≥ minimum coverage."""
    y, p = np.asarray(y_val), np.asarray(p_val)
    confidence = np.maximum(p, 1 - p)
    pred = (p >= 0.5).astype(int)
    curve = []
    for cut in np.round(np.arange(0.5, 1.0, 0.025), 3):
        covered = confidence >= cut
        coverage = float(covered.mean()) if len(y) else 0.0
        risk = float((pred[covered] != y[covered]).mean()) if covered.any() else None
        curve.append({"threshold": float(cut), "coverage": round(coverage, 4),
                      "risk": None if risk is None else round(risk, 4)})  # fmt: skip
    chosen = next(
        (c for c in curve if c["risk"] is not None and c["risk"] <= TARGET_RISK
         and c["coverage"] >= MIN_COVERAGE),
        None,
    )  # fmt: skip
    return {
        "rule": f"smallest threshold with validation risk ≤ {TARGET_RISK} and coverage ≥ "
        f"{MIN_COVERAGE}",
        "threshold": chosen["threshold"] if chosen else 0.5,
        "target_met": chosen is not None,
        "validation_curve": curve,
    }


def bootstrap_ci(groups, y, preds: dict[str, np.ndarray], compare: tuple[str, str] | None):
    """Resample whole site groups, so nearby cases never count as independent evidence."""
    rng = np.random.default_rng(11)
    groups = np.asarray(groups)
    unique = np.unique(groups)
    index = {g: np.where(groups == g)[0] for g in unique}
    scores = defaultdict(list)
    diffs = []
    for _ in range(BOOTSTRAP):
        sample = np.concatenate([index[g] for g in rng.choice(unique, size=len(unique))])
        ys = np.asarray(y)[sample]
        if len(set(ys)) < 2:
            continue
        values = {name: macro_f1(ys, p[sample]) for name, p in preds.items()}
        for name, v in values.items():
            scores[name].append(v)
        if compare:
            diffs.append(values[compare[0]] - values[compare[1]])

    def interval(v):
        return None if not v else [round(float(np.percentile(v, 2.5)), 4),
                                   round(float(np.percentile(v, 97.5)), 4)]  # fmt: skip

    return {
        "method": f"site-group bootstrap, {BOOTSTRAP} resamples",
        "macro_f1_ci": {k: interval(v) for k, v in scores.items()},
        "paired_difference_ci": interval(diffs),
    }


# ---------------------------------------------------------------------------------------------
# Training and evaluation


def matrix(rows: list[dict], columns: list[str]) -> np.ndarray:
    return np.array(
        [[np.nan if r["features"].get(c) is None else float(r["features"][c]) for c in columns]
         for r in rows],
        dtype=float,
    )  # fmt: skip


def rule_predictions(rows) -> tuple[np.ndarray, np.ndarray]:
    """P04 source rule as a baseline: industrial=1, non-industrial=0, unknown=abstain."""
    pred = np.array([1 if r["weak_label"] == "INDUSTRIAL" else 0 for r in rows])
    covered = np.array([r["weak_label"] is not None for r in rows])
    return pred, covered


def fit_xgb(x, y):
    from xgboost import XGBClassifier

    positives = max(1, int(np.sum(y)))
    negatives = max(1, len(y) - positives)
    model = XGBClassifier(**XGB_PARAMS, scale_pos_weight=negatives / positives,
                          eval_metric="logloss")  # fmt: skip
    model.fit(x, y)
    return model


def fit_platt(y_val, p_val) -> dict:
    y = np.asarray(y_val)
    if min((y == 1).sum(), (y == 0).sum()) < 5:
        return {"method": "none", "reason": "fewer than 5 validation cases in a class"}
    from sklearn.linear_model import LogisticRegression

    eps = 1e-6
    logit = np.log(np.clip(p_val, eps, 1 - eps) / (1 - np.clip(p_val, eps, 1 - eps)))
    lr = LogisticRegression(C=1e6, max_iter=1000).fit(logit.reshape(-1, 1), y)
    return {"method": "platt", "a": float(lr.coef_[0][0]), "b": float(lr.intercept_[0])}


def apply_calibration(cal: dict, p) -> np.ndarray:
    p = np.asarray(p, dtype=float)
    if cal["method"] != "platt":
        return p
    eps = 1e-6
    logit = np.log(np.clip(p, eps, 1 - eps) / (1 - np.clip(p, eps, 1 - eps)))
    return 1 / (1 + np.exp(-(cal["a"] * logit + cal["b"])))


def load_training_rows(conn, set_id) -> list[dict]:
    labels = resolved_labels(conn, set_id)
    rows = []
    for r in conn.execute(
        text("""
        SELECT c.id,c.split,c.split_group,c.region_id,c.forward_period,c.as_of,c.site_id,
            f.features,f.weak_label,f.silver_label,f.nasa_type_majority
        FROM label_cases c JOIN case_features f
            ON f.case_set_id=c.case_set_id AND f.case_id=c.id AND f.feature_version=:v
        WHERE c.case_set_id=:s ORDER BY c.id
    """),
        {"s": set_id, "v": FEATURE_VERSION},
    ).mappings():
        item = dict(r) | {"resolved": labels[r["id"]]}
        item["target"] = binary_target(item["resolved"]["label"])
        rows.append(item)
    return rows


def train_and_evaluate(settings: Settings, set_ref: str, *, dry_run_weak: bool = False) -> dict:
    with batch_engine(settings) as engine, engine.connect() as conn:
        set_id = case_set_id(conn, set_ref)
        rows = load_training_rows(conn, set_id)
    if not rows:
        raise ValueError("no case features; run the features step first")
    policy = "DRY_RUN_WEAK" if dry_run_weak else "REVIEWED"
    allowed_train = {"GOLD", "SILVER", "WEAK"} if dry_run_weak else {"GOLD", "SILVER"}

    def usable(r, split):
        if r["split"] != split or r["target"] is None:
            return False
        if split == "TEST":
            return (
                (r["resolved"]["tier"] in allowed_train)
                if dry_run_weak
                else (r["resolved"]["test_eligible"])
            )
        return r["resolved"]["tier"] in allowed_train

    train = [r for r in rows if usable(r, "TRAIN")]
    val = [r for r in rows if usable(r, "VALIDATION")]
    test = [r for r in rows if usable(r, "TEST")]
    labels_sha = hashlib.sha256(
        json.dumps(sorted((r["id"], r["resolved"]["label"], r["resolved"]["tier"],
                           r["resolved"]["basis"]) for r in rows)).encode()
    ).hexdigest()  # fmt: skip

    def support(items):
        return {"INDUSTRIAL": sum(r["target"] == 1 for r in items),
                "NON_INDUSTRIAL": sum(r["target"] == 0 for r in items)}  # fmt: skip

    report = {
        "model_version": MODEL_VERSION,
        "feature_version": FEATURE_VERSION,
        "label_policy": f"{LABEL_POLICY}/{policy}",
        "labels_sha256": labels_sha,
        "support": {"train": support(train), "validation": support(val), "test": support(test)},
        "tiers_used": sorted({r["resolved"]["tier"] for r in train + val + test}),
    }
    enough_train = min(report["support"]["train"].values()) >= MIN_TRAIN_PER_CLASS
    enough_test = min(report["support"]["test"].values()) >= MIN_TEST_PER_CLASS_REPORT
    status = "DRY_RUN_NOT_EVIDENCE" if dry_run_weak else "INSUFFICIENT_LABELS"
    run_id = uuid4()
    out_dir = Path(settings.object_store_local_path).parent / "models" / str(run_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not enough_train or not val or not enough_test:
        report["status"] = "INSUFFICIENT_LABELS" if not dry_run_weak else status
        report["reason"] = (
            f"Need ≥{MIN_TRAIN_PER_CLASS} training and ≥{MIN_TEST_PER_CLASS_REPORT} "
            "test cases per class"
            + ("" if dry_run_weak else " with reviewed test labels (two agreeing reviews or "
               "adjudication)")
            + "."
        )  # fmt: skip
        return save_run(settings, set_id, run_id, out_dir, report, None, [], policy)

    y_train = np.array([r["target"] for r in train])
    y_val = np.array([r["target"] for r in val])
    y_test = np.array([r["target"] for r in test])
    models, raw_val, raw_test = {}, {}, {}
    for name, columns in FEATURE_SETS.items():
        model = fit_xgb(matrix(train, columns), y_train)
        models[name] = (model, columns)
        raw_val[name] = model.predict_proba(matrix(val, columns))[:, 1]
        raw_test[name] = model.predict_proba(matrix(test, columns))[:, 1]
    calibration = fit_platt(y_val, raw_val["full"])
    p_val = apply_calibration(calibration, raw_val["full"])
    p_test = apply_calibration(calibration, raw_test["full"])
    abstention = choose_abstention(y_val, p_val)

    rule_pred, rule_covered = rule_predictions(test)
    preds = {name: (raw_test[name] >= 0.5).astype(int) for name in FEATURE_SETS}
    preds["full_calibrated"] = (p_test >= 0.5).astype(int)
    evaluation = {name: classification_metrics(y_test, p) for name, p in preds.items()}
    evaluation["rules_p04_on_covered"] = classification_metrics(
        y_test[rule_covered], rule_pred[rule_covered]
    ) | {"coverage": round(float(rule_covered.mean()), 4)}
    confidence = np.maximum(p_test, 1 - p_test)
    covered = confidence >= abstention["threshold"]
    evaluation["full_with_abstention"] = classification_metrics(
        y_test[covered], preds["full_calibrated"][covered]
    ) | {"coverage": round(float(covered.mean()), 4)}
    evaluation["brier_full_calibrated"] = round(float(np.mean((p_test - y_test) ** 2)), 4)
    evaluation["reliability_full_calibrated"] = reliability(y_test, p_test)
    try:
        from sklearn.metrics import average_precision_score

        evaluation["pr_auc_full"] = round(float(average_precision_score(y_test, p_test)), 4)
    except ValueError:
        evaluation["pr_auc_full"] = None
    baselines = {"thermal_history": macro_f1(y_test, preds["thermal_history"]),
                 "rules_p04_forced": macro_f1(y_test, rule_pred)}  # fmt: skip
    best_baseline = max(baselines, key=baselines.get)
    compare_pred = preds["thermal_history"] if best_baseline == "thermal_history" else rule_pred
    ci = bootstrap_ci(
        [r["split_group"] for r in test],
        y_test,
        {"full": preds["full"], best_baseline: compare_pred},
        ("full", best_baseline),
    )
    by_region = defaultdict(lambda: {"cases": 0, "errors": 0})
    for r, pred in zip(test, preds["full_calibrated"], strict=True):
        by_region[r["region_id"]]["cases"] += 1
        by_region[r["region_id"]]["errors"] += int(pred != r["target"])
    errors = sorted(
        (
            {"case_id": r["id"], "region_id": r["region_id"], "label": r["resolved"]["label"],
             "tier": r["resolved"]["tier"], "p_industrial": round(float(p), 4)}
            for r, p in zip(test, p_test, strict=True)
            if (p >= 0.5) != (r["target"] == 1)
        ),
        key=lambda e: -abs(e["p_industrial"] - 0.5),
    )[:15]  # fmt: skip
    nasa = [(r["nasa_type_majority"], r["target"]) for r in test if r["nasa_type_majority"]
            is not None]  # fmt: skip
    report |= {
        "evaluation": evaluation,
        "baselines_macro_f1": baselines | {"best": best_baseline},
        "bootstrap": ci,
        "errors_by_region": dict(by_region),
        "error_examples": errors,
        "calibration": calibration,
        "abstention": abstention,
        "known_site_future": known_site_future(rows, dry_run_weak),
        "nasa_type_retrospective": {
            "cases_with_type": len(nasa),
            "note": "NASA SP 'type' (0 = presumed vegetation fire, 2 = other static land "
            "source) compared retrospectively; not a label and not a model input.",
            "type2_industrial_rate": _rate(nasa, 2),
            "type0_industrial_rate": _rate(nasa, 0),
        },
    }
    if dry_run_weak:
        report["status"] = "DRY_RUN_NOT_EVIDENCE"
        report["reason"] = (
            "Weak (rule-derived) labels were used for training and testing to exercise the "
            "pipeline. Rules agreeing with a model trained on rules is circular: these numbers "
            "are not performance evidence."
        )
        report["do_not_quote"] = (
            "Scores in this file measure agreement with the project's own rules, not accuracy. "
            "Never present them as model performance."
        )
    else:
        diff = ci["paired_difference_ci"]
        promotable = (
            min(report["support"]["test"].values()) >= MIN_TEST_PER_CLASS_PROMOTE
            and diff is not None
            and diff[0] > 0
        )
        report["status"] = "PROMOTED" if promotable else "EVALUATED_NOT_PROMOTED"
        report["reason"] = (
            "Beats the best baseline with a site-group bootstrap interval above zero."
            if promotable
            else "Promotion needs ≥30 reviewed test cases per class and a paired macro-F1 "
            "gain over the best baseline whose interval lies above zero."
        )
    predictions = [
        {"case_id": r["id"], "split": "TEST", "region_id": r["region_id"],
         "label": r["resolved"]["label"], "tier": r["resolved"]["tier"],
         "p_industrial": round(float(p), 5), "abstained": bool(c < abstention["threshold"])}
        for r, p, c in zip(test, p_test, confidence, strict=True)
    ]  # fmt: skip
    return save_run(settings, set_id, run_id, out_dir, report, models["full"], predictions,
                    policy, calibration)  # fmt: skip


def _rate(pairs, value):
    matching = [t for v, t in pairs if v == value]
    return None if not matching else round(sum(matching) / len(matching), 4)


def known_site_future(rows, dry_run_weak) -> dict:
    """Train on earlier cases, test on later cases at sites seen in training."""
    ok = {"GOLD", "SILVER", "WEAK"} if dry_run_weak else {"GOLD", "SILVER"}
    before = [r for r in rows if r["forward_period"] == "BEFORE" and r["target"] is not None
              and r["resolved"]["tier"] in ok]  # fmt: skip
    seen = {r["split_group"] for r in before}
    after = [
        r
        for r in rows
        if r["forward_period"] == "AFTER" and r["target"] is not None
        and r["split_group"] in seen
        and (r["resolved"]["tier"] in ok if dry_run_weak else r["resolved"]["tier"] == "GOLD")
    ]  # fmt: skip
    y_before = [r["target"] for r in before]
    y_after = [r["target"] for r in after]
    if min(y_before.count(0), y_before.count(1)) < 5 or len(set(y_after)) < 2:
        return {"status": "INSUFFICIENT_LABELS", "train_cases": len(before),
                "test_cases": len(after)}  # fmt: skip
    model = fit_xgb(matrix(before, FEATURES), np.array(y_before))
    pred = (model.predict_proba(matrix(after, FEATURES))[:, 1] >= 0.5).astype(int)
    return {"status": "EVALUATED", "train_cases": len(before), "test_cases": len(after),
            "metrics": classification_metrics(y_after, pred)}  # fmt: skip


def save_run(settings, set_id, run_id, out_dir, report, full_model, predictions, policy,
             calibration=None) -> dict:  # fmt: skip
    files = {}

    def write(name, content: bytes):
        (out_dir / name).write_bytes(content)
        files[name] = hashlib.sha256(content).hexdigest()

    if full_model is not None:
        model, columns = full_model
        model.save_model(str(out_dir / "model.json"))
        files["model.json"] = hashlib.sha256((out_dir / "model.json").read_bytes()).hexdigest()
        write(
            "features.json",
            json.dumps(
                {"version": FEATURE_VERSION, "columns": columns, "xgb_params": XGB_PARAMS}, indent=2
            ).encode(),
        )
        write("calibration.json", json.dumps(calibration, indent=2).encode())
    if predictions:
        buffer = io_csv(predictions)
        write("test_predictions.csv", buffer)
    report["model_version_id"] = str(run_id)
    report["created_at"] = datetime.now(UTC).isoformat()
    write("metrics.json", json.dumps(report, indent=2, default=str).encode())
    write("model_card.md", model_card(report).encode())
    manifest = json.dumps({"files": files, "case_set_id": str(set_id)}, indent=2, sort_keys=True)
    write("manifest.json", manifest.encode())
    artifact_sha = hashlib.sha256(manifest.encode()).hexdigest()
    with database_engine(settings) as engine, engine.begin() as conn:
        conn.execute(
            text("""
            INSERT INTO model_versions (id,case_set_id,algorithm,feature_version,label_policy,
                labels_sha256,artifact_dir,artifact_sha256,status,metrics,created_at)
            VALUES (:id,:s,:alg,:fv,:policy,:labels,:dir,:sha,:status,CAST(:metrics AS jsonb),
                :now)
        """),
            {
                "id": run_id,
                "s": set_id,
                "alg": MODEL_VERSION,
                "fv": FEATURE_VERSION,
                "policy": report["label_policy"],
                "labels": report["labels_sha256"],
                "dir": str(out_dir),
                "sha": artifact_sha,
                "status": report["status"],
                "metrics": json.dumps(summary_of(report), default=str),
                "now": datetime.now(UTC),
            },
        )
    return {"model_version_id": str(run_id), "status": report["status"],
            "artifact_dir": str(out_dir), "artifact_sha256": artifact_sha,
            "support": report["support"], "reason": report.get("reason")}  # fmt: skip


def io_csv(rows: list[dict]) -> bytes:
    import io

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode()


def summary_of(report: dict) -> dict:
    keep = {"status", "support", "label_policy", "reason", "baselines_macro_f1"}
    out = {k: v for k, v in report.items() if k in keep}
    evaluation = report.get("evaluation")
    if evaluation:
        out["macro_f1"] = {k: v["macro_f1"] for k, v in evaluation.items()
                           if isinstance(v, dict) and "macro_f1" in v}  # fmt: skip
        out["brier"] = evaluation.get("brier_full_calibrated")
    return out


def model_card(report: dict) -> str:
    status = report["status"]
    s = report["support"]
    lines = [
        f"# Model card — {MODEL_VERSION}",
        "",
        f"Status: **{status}**. {report.get('reason', '')}",
        "",
        "## What it is",
        "Gradient-boosted trees (XGBoost) predicting whether a VIIRS thermal episode is "
        "industrial or non-industrial, from episode thermal statistics, the location's earlier "
        "detections, mapped OSM industry and ESA WorldCover 2021 land cover. Raw coordinates, "
        "IDs, names, dates and NASA's type field are not inputs.",
        "",
        "## Intended use",
        "Research support for analysts reviewing thermal detections. Not for alerts, not for "
        "confirming incidents, not a probability of an accident.",
        "",
        "## Data and labels",
        f"- Feature version `{report['feature_version']}`; label policy "
        f"`{report['label_policy']}`; labels snapshot `{report['labels_sha256'][:16]}…`.",
        f"- Training support: {s['train']}; validation: {s['validation']}; test: {s['test']}.",
        f"- Label tiers used: {', '.join(t for t in report['tiers_used'] if t) or 'none'}.",
        "- GOLD = human review with cited evidence (test cases need two agreeing reviews or "
        "an adjudication). SILVER = registry corroboration (WRI GPPD v1.3.0, thermal power "
        "plants within 1.5 km) or a single review. WEAK = this project's P04 rules.",
        "",
        "## Evaluation protocols",
        "- Unseen-site: TRAIN / VALIDATION / TEST are disjoint site groups (sites within 2 km "
        "merged), frozen before labelling.",
        "- Known-site future: trained on earlier cases, tested on later cases at seen sites.",
        "- Group bootstrap intervals resample whole site groups.",
        "",
    ]
    evaluation = report.get("evaluation")
    if evaluation and status != "DRY_RUN_NOT_EVIDENCE":
        lines += ["## Results (reviewed test labels)", ""]
        for name, v in evaluation.items():
            if isinstance(v, dict) and "macro_f1" in v:
                lines.append(
                    f"- `{name}`: macro-F1 {v['macro_f1']}, accuracy {v['accuracy']}"
                    + (f", coverage {v['coverage']}" if "coverage" in v else "")
                )
        lines += [
            f"- Brier (calibrated full model): {evaluation['brier_full_calibrated']}",
            f"- Paired macro-F1 difference vs best baseline, 95% interval: "
            f"{report['bootstrap']['paired_difference_ci']}",
            "",
        ]
    elif evaluation:
        lines += ["## Pipeline dry run", "",
                  "Numbers from this run are withheld from the card on purpose: training and "
                  "test labels came from the same rules, so agreement is circular. See "
                  "metrics.json only to confirm the pipeline executes.", ""]  # fmt: skip
    else:
        lines += ["## Results", "", "No evaluation: not enough reviewed labels.", ""]
    lines += [
        "## Limitations",
        "- Pilot regions in India only; March–September 2026; NOAA-20 VIIRS only.",
        "- OSM is incomplete and dated after most observations (retrospective context).",
        "- WorldCover is from 2021; land use may have changed.",
        "- Thresholds for abstention are chosen on validation data and are not a guarantee.",
        "- Abnormal-behaviour detection is not part of this model; see the P04 rules.",
        "",
        "## Reproducibility",
        f"Artifacts are JSON files hashed in manifest.json; model version id "
        f"`{report['model_version_id']}`; created {report['created_at']}.",
        "",
    ]
    return "\n".join(lines)


def extract_case_landcover(settings: Settings, set_ref: str) -> dict:
    """Land cover only for the representative observation of each case, one read per tile."""
    from thermoscope.landcover import extract_landcover

    with database_engine(settings) as engine, engine.connect() as conn:
        set_id = case_set_id(conn, set_ref)
        mode = DataMode(
            conn.execute(
                text("SELECT data_mode FROM case_sets WHERE id=:s"), {"s": set_id}
            ).scalar_one()
        )
        by_region = defaultdict(list)
        for region, rep in conn.execute(
            text("""SELECT region_id,representative_observation_id FROM label_cases
                    WHERE case_set_id=:s"""),
            {"s": set_id},
        ):
            by_region[region].append(rep)
    totals = defaultdict(int)
    for region, ids in sorted(by_region.items()):
        report = extract_landcover(settings, region, mode, observation_ids=ids)
        totals["summarized"] += report["summarized"]
        totals["failed"] += report["failed"]
    return {"case_set_id": str(set_id)} | dict(totals)
