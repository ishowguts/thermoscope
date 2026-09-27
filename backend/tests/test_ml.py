"""P05 model pipeline pieces: features without leakage, metrics, abstention, group bootstrap."""

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from thermoscope.ml import (
    FEATURE_SETS,
    FEATURES,
    apply_calibration,
    binary_target,
    bootstrap_ci,
    choose_abstention,
    classification_metrics,
    episode_features,
    fit_platt,
    known_site_future,
    landcover_features,
    model_card,
    osm_features,
    rule_predictions,
    summary_of,
)

T0 = datetime(2026, 5, 1, 20, 30, tzinfo=UTC)


def member(minutes=0, frp=5.0, sat="N20", dn="N", conf="n", i4=330.0, i5=295.0):
    return {"acquired_at": T0 + timedelta(minutes=minutes), "frp_mw": frp, "satellite": sat,
            "daynight": dn, "confidence": conf, "i4": i4, "i5": i5, "scan": 0.4,
            "track": 0.4}  # fmt: skip


def test_episode_features_use_per_overpass_maxima_and_fractions():
    f = episode_features([member(frp=5), member(frp=9, conf="h"), member(720, frp=2, dn="D")])
    assert f["obs_count"] == 3 and f["overpass_count"] == 2
    assert f["frp_max"] == 9 and f["frp_overpass_median"] == 5.5  # per-pass maxima 9 and 2
    assert f["duration_h"] == 12 and f["night_fraction"] == pytest.approx(2 / 3)
    assert f["high_conf_fraction"] == pytest.approx(1 / 3)
    assert f["bt_diff_median"] == 35


def test_feature_lists_hold_no_identity_location_date_or_nasa_type():
    banned = ("lat", "lon", "latitude", "longitude", "date", "month", "region", "site", "id",
              "nasa_type", "type", "name", "registry", "gppd")  # fmt: skip
    for column in FEATURES:
        assert column not in banned and not column.endswith("_id")
    for proxy in ("coverage_90", "coverage_180", "active_days_180"):
        assert proxy not in FEATURES  # rise with the date because the archive starts in March
    assert set(FEATURE_SETS["full"]) == set(FEATURES)
    assert len(FEATURES) == len(set(FEATURES))


def test_osm_and_landcover_features():
    candidates = [
        {"relation": "INSIDE_SUPPORT", "facility_type": "REFINERY", "primary_tag": "man_made=flare",
         "distance_m": 0.0},
        {"relation": "NEARBY", "facility_type": "POWER", "primary_tag": "power=plant",
         "distance_m": 900.0},
    ]  # fmt: skip
    f = osm_features(candidates, True)
    assert f["has_refinery"] == 1 and f["has_flare_tag"] == 1 and f["has_power"] == 0
    assert f["n_industrial_in_support"] == 1 and f["n_industrial_2km"] == 2
    assert f["has_nonthermal_power"] == 0
    assert osm_features([], True)["nearest_industrial_m"] == 5000.0  # covered, nothing mapped
    uncovered = osm_features([], False)  # incomplete OSM coverage is missing, not zero
    assert uncovered["osm_covered"] == 0
    assert all(v is None for k, v in uncovered.items() if k != "osm_covered")
    solar = {
        "relation": "INSIDE_SUPPORT",
        "facility_type": "POWER",
        "primary_tag": "power=plant",
        "distance_m": 0.0,
        "power_source": "solar",
        "thermal_source_candidate": False,
    }
    only_solar = osm_features([solar], True)  # fmt: skip
    assert only_solar["has_power"] == 0 and only_solar["n_industrial_in_support"] == 0
    assert only_solar["has_nonthermal_power"] == 1 and only_solar["nearest_industrial_m"] == 5000
    land = {"support": {"valid_fraction": 1.0,
                        "fractions": [{"class": "CROPLAND", "fraction": 0.7},
                                      {"class": "MANGROVES", "fraction": 0.1}]},
            "context": {"valid_fraction": 1.0, "fractions": {"CROPLAND": 0.4}}}  # fmt: skip
    lc = landcover_features(land)
    assert lc["lc_crop"] == 0.7 and lc["lc_wetland"] == 0.1 and lc["lc_crop_1km"] == 0.4
    assert all(v is None for v in landcover_features(None).values())


def test_binary_target_drops_unresolved():
    assert [binary_target(x) for x in ("INDUSTRIAL", "AGRICULTURAL_BURN", "UNRESOLVED", None)] == [
        1, 0, None, None]  # fmt: skip


def test_metrics_and_confusion_matrix():
    m = classification_metrics([1, 1, 0, 0], [1, 0, 0, 0])
    assert m["confusion_matrix"]["counts"] == [[1, 1], [0, 2]]
    assert m["INDUSTRIAL"] == {"precision": 1.0, "recall": 0.5, "f1": 0.6667}
    assert m["accuracy"] == 0.75


def test_rule_baseline_abstains_on_unknown():
    pred, covered = rule_predictions(
        [{"weak_label": "INDUSTRIAL"}, {"weak_label": "AGRICULTURAL_BURN"}, {"weak_label": None}]
    )
    assert pred.tolist() == [1, 0, 0] and covered.tolist() == [True, True, False]


def test_abstention_threshold_meets_target_on_validation_or_says_so():
    y = np.array([1] * 50 + [0] * 50)
    # 16 of 100 wrong, all with low confidence: risk 0.16 at 0.5, zero once they abstain.
    p = np.array([0.95] * 42 + [0.45] * 8 + [0.05] * 42 + [0.55] * 8)
    choice = choose_abstention(y, p)
    assert choice["target_met"] and choice["threshold"] == 0.575
    noisy = choose_abstention(np.array([1, 0] * 20), np.full(40, 0.9))
    assert not noisy["target_met"] and noisy["threshold"] == 0.5


def test_platt_calibration_is_monotone_and_needs_both_classes():
    pytest.importorskip("sklearn")
    assert fit_platt([1, 1, 1], [0.9, 0.8, 0.7])["method"] == "none"
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 200)
    p = np.clip(0.2 + 0.6 * y + rng.normal(0, 0.1, 200), 0.01, 0.99)
    cal = fit_platt(y, p)
    out = apply_calibration(cal, np.array([0.1, 0.5, 0.9]))
    assert cal["method"] == "platt" and out[0] < out[1] < out[2]


def test_group_bootstrap_resamples_whole_groups():
    groups = ["g1"] * 5 + ["g2"] * 5 + ["g3"] * 5 + ["g4"] * 5
    y = np.array([1] * 10 + [0] * 10)
    perfect = y.copy()
    random = np.array([1, 0] * 10)
    ci = bootstrap_ci(groups, y, {"model": perfect, "base": random}, ("model", "base"))
    assert ci["macro_f1_ci"]["model"] == [1.0, 1.0]
    assert ci["paired_difference_ci"][0] > 0


def test_dry_run_card_withholds_numbers():
    report = {"status": "DRY_RUN_NOT_EVIDENCE", "reason": "circular", "feature_version": "v",
              "label_policy": "p", "labels_sha256": "0" * 64, "tiers_used": ["WEAK"],
              "support": {"train": {}, "validation": {}, "test": {}},
              "evaluation": {"full": {"macro_f1": 0.99, "accuracy": 0.99}},
              "model_version_id": "x", "created_at": "now"}  # fmt: skip
    card = model_card(report)
    assert "DRY_RUN_NOT_EVIDENCE" in card and "0.99" not in card


def synthetic_rows(n_groups=60, per_group=4, seed=3):
    """Separable synthetic cases: industrial ones persist at night; others are daytime bursts."""
    rng = np.random.default_rng(seed)
    rows = []
    for g in range(n_groups):
        split = ("TRAIN", "TRAIN", "TRAIN", "VALIDATION", "TEST")[g % 5]
        industrial = g % 2 == 0
        for k in range(per_group):
            features = {c: None for c in FEATURES} | {"history_complete": True}
            features |= {
                "night_fraction": float(np.clip((0.8 if industrial else 0.2)
                                                + rng.normal(0, 0.15), 0, 1)),
                "active_days_90": float(rng.poisson(40 if industrial else 3)),
                "lc_crop": float(np.clip((0.1 if industrial else 0.7) + rng.normal(0, 0.2), 0, 1)),
                "frp_max": float(rng.gamma(2, 10)),
            }  # fmt: skip
            label = "INDUSTRIAL" if industrial else "AGRICULTURAL_BURN"
            tier = "GOLD"
            basis = "TWO_REVIEWERS_AGREE" if split == "TEST" else "ONE_REVIEWER"
            rows.append({
                "id": f"{g:03d}{k}".ljust(64, "0"), "split": split, "split_group": f"g{g}",
                "region_id": "r1" if g < 30 else "r2", "forward_period": "BEFORE",
                "as_of": T0, "site_id": f"s{g}", "features": features,
                "weak_label": label if k % 2 else None, "silver_label": None,
                "nasa_type_majority": None,
                "resolved": {"label": label, "tier": tier, "basis": basis,
                             "test_eligible": split == "TEST"},
                "target": binary_target(label),
            })  # fmt: skip
    return rows


def test_training_reports_baselines_intervals_and_never_promotes_small_tests(monkeypatch, tmp_path):
    pytest.importorskip("xgboost")
    pytest.importorskip("sklearn")
    import contextlib

    import thermoscope.ml as ml

    captured = {}

    @contextlib.contextmanager
    def fake_engine(settings):
        yield type("E", (), {"connect": lambda self: contextlib.nullcontext(None)})()

    monkeypatch.setattr(ml, "batch_engine", fake_engine)
    monkeypatch.setattr(ml, "case_set_id", lambda conn, ref: "set")
    monkeypatch.setattr(ml, "superseded_by", lambda conn, set_id: None)
    monkeypatch.setattr(ml, "case_set_grouping", lambda conn, set_id: "facility-aware-v1")
    monkeypatch.setattr(ml, "load_training_rows", lambda conn, set_id: synthetic_rows())

    def fake_save(settings, set_id, run_id, out_dir, report, model, predictions, policy,
                  calibration=None):  # fmt: skip
        captured.update(report=report, model=model, predictions=predictions)
        return {"status": report["status"]}

    monkeypatch.setattr(ml, "save_run", fake_save)
    settings = type("S", (), {"object_store_local_path": tmp_path / "objects"})()
    result = ml.train_and_evaluate(settings, "set")
    report = captured["report"]
    assert report["support"]["test"] == {"INDUSTRIAL": 24, "NON_INDUSTRIAL": 24}
    # 24 per class is enough to report but below the 30 needed to promote.
    assert result["status"] == "EVALUATED_NOT_PROMOTED"
    expected = {"full", "thermal_history", "full_minus_osm", "rules_p04_on_covered",
                "full_with_abstention"}  # fmt: skip
    assert set(report["evaluation"]) >= expected
    assert report["evaluation"]["full"]["macro_f1"] > 0.8  # the synthetic signal is learnable
    assert report["bootstrap"]["method"].startswith("site-group bootstrap")
    assert report["calibration"]["method"] == "platt"
    assert len(captured["predictions"]) == 48
    assert all(0 <= p["p_industrial"] <= 1 for p in captured["predictions"])

    held = report["held_out_region"]
    assert held["status"] == "EVALUATED" and held["support"] == report["support"]["test"]
    assert set(held["regions"]) == {"r1", "r2"}  # each region scored by the other's model

    ml.train_and_evaluate(settings, "set", dry_run_weak=True)
    assert captured["report"]["status"] == "DRY_RUN_NOT_EVIDENCE"

    # Cases without a complete history window are set aside, never imputed.
    rows = synthetic_rows()
    for r in rows[:8]:
        r["features"]["history_complete"] = False
    monkeypatch.setattr(ml, "load_training_rows", lambda conn, set_id: rows)
    ml.train_and_evaluate(settings, "set")
    policy = captured["report"]["history_policy"]
    assert policy["cases_eligible"] == len(rows) - 8
    assert sum(policy["cases_excluded_by_split"].values()) == 8

    # A superseded case set cannot be evaluated at all.
    monkeypatch.setattr(ml, "superseded_by", lambda conn, set_id: "newer-set")
    with pytest.raises(ValueError, match="superseded"):
        ml.train_and_evaluate(settings, "set")


def test_dry_run_scores_never_reach_the_model_list():
    report = {"status": "DRY_RUN_NOT_EVIDENCE", "support": {}, "label_policy": "p",
              "reason": "r", "do_not_quote": "n", "baselines_macro_f1": {"full": 0.99},
              "evaluation": {"full": {"macro_f1": 0.99}}}  # fmt: skip
    summary = summary_of(report)
    assert "0.99" not in str(summary) and summary["do_not_quote"] == "n"


def test_known_site_future_needs_reviewed_support_in_both_periods():
    rows = synthetic_rows()
    for r in rows:
        r["forward_period"] = "AFTER" if r["split"] == "TEST" else "BEFORE"
    assert known_site_future(rows, False)["status"] == "INSUFFICIENT_LABELS"  # groups unseen
    for r in rows:
        if r["split"] == "TEST":
            r["split_group"] = "g0" if r["target"] == 1 else "g1"
    result = known_site_future(rows, False)
    assert result["status"] == "EVALUATED" and result["test_cases"] == 48
    for r in rows:
        r["resolved"] = r["resolved"] | {"test_eligible": False}
    assert known_site_future(rows, False)["status"] == "INSUFFICIENT_LABELS"
