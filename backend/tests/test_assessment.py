import math
from datetime import UTC, date, datetime, timedelta

import pytest
from thermoscope.assessment import (
    MIN_LOG_SCALE,
    Basis,
    Coverage,
    Detection,
    assess,
    behaviour_rule,
    covered_dates,
    eligible,
    history_features,
    per_overpass_max,
    priority_rule,
    source_rule,
)

AS_OF = datetime(2026, 4, 6, 21, tzinfo=UTC)
FULL = [Coverage(date(2025, 10, 1), date(2026, 4, 6), datetime(2026, 4, 7, tzinfo=UTC))]


def det(days_before, frp, dn="N", sat="N20", available=None, hours=0, ident=None):
    at = AS_OF - timedelta(days=days_before, hours=hours)
    return Detection(ident or f"{days_before}-{hours}-{frp}", at, frp, sat, dn, "VIIRS_NOAA20_NRT",
                     available)  # fmt: skip


def nightly(values, start=2):
    return [det(start + 3 * i, v) for i, v in enumerate(values)]


def features(detections, runs=FULL, basis=Basis.RETROSPECTIVE):
    return history_features(detections, runs, AS_OF, basis)


def test_future_and_unknown_availability_are_excluded():
    later = det(-1, 9.0)
    known = det(3, 2.0, available=AS_OF - timedelta(days=2))
    late_known = det(3, 2.0, available=AS_OF + timedelta(hours=1), ident="late")
    unknown = det(4, 2.0)
    assert eligible([later, known, late_known, unknown], AS_OF, Basis.RETROSPECTIVE) == [
        known,
        late_known,
        unknown,
    ]
    assert eligible([later, known, late_known, unknown], AS_OF, Basis.OPERATIONAL) == [known]
    result = features([later, known, unknown], basis=Basis.OPERATIONAL)
    assert result["excluded_after_as_of"] == 1 and result["excluded_unknown_availability"] == 1
    assert result["latest_input_acquired_at"] <= AS_OF


def test_operational_coverage_only_counts_runs_already_received():
    runs = [
        Coverage(date(2026, 3, 1), date(2026, 3, 5), AS_OF - timedelta(days=1)),
        Coverage(date(2026, 3, 6), date(2026, 3, 10), AS_OF + timedelta(days=1)),
    ]
    assert len(covered_dates(runs, AS_OF, Basis.RETROSPECTIVE)) == 10
    assert len(covered_dates(runs, AS_OF, Basis.OPERATIONAL)) == 5


def test_frp_is_the_per_overpass_maximum_never_a_sum():
    same_pass = [det(1, 2.0, ident="a"), det(1, 3.0, ident="b"), det(1, None, ident="c")]
    assert list(per_overpass_max(same_pass).values()) == [3.0]


def test_mad_zero_uses_a_floor_and_flags_it():
    history = nightly([2.0] * 6)
    same = behaviour_rule(features(history + [det(0, 2.0)]))
    assert same["label"] == "RECURRENT_WITHIN_BASELINE"
    assert (
        same["comparisons"]["N20/N"]["mad_zero"]
        and same["comparisons"]["N20/N"]["scale_floor_applied"]
    )
    spike = behaviour_rule(features(history + [det(0, 10.0)]))
    assert spike["label"] == "ABNORMAL_RELATIVE_TO_BASELINE" and spike["direction"] == "HIGHER"
    expected = (math.log1p(10) - math.log1p(2)) / MIN_LOG_SCALE  # the floor is the divisor
    assert spike["comparisons"]["N20/N"]["robust_z"] == pytest.approx(expected, abs=1e-3)
    assert any("MAD = 0" in reason for reason in spike["reasons"])
    huge = behaviour_rule(features(history + [det(0, 1e9)]))
    assert huge["comparisons"]["N20/N"]["capped"] and huge["comparisons"]["N20/N"]["robust_z"] == 50


def test_varied_history_within_and_below_baseline():
    history = nightly([1.5, 2.0, 2.5, 1.8, 2.2, 3.0, 1.2, 2.4])
    within = behaviour_rule(features(history + [det(0, 2.3)]))
    assert within["label"] == "RECURRENT_WITHIN_BASELINE"
    assert "not certified safe" in within["reasons"][-1]
    low = behaviour_rule(features(history + [det(0, 0.01)]))
    assert low["label"] == "ABNORMAL_RELATIVE_TO_BASELINE" and low["direction"] == "LOWER"


def test_insufficient_history_sensor_change_and_gaps():
    few = behaviour_rule(features(nightly([2.0] * 4) + [det(0, 2.0)]))
    assert few["label"] == "INSUFFICIENT_HISTORY" and few["rule"] == "B3_UNMATCHED_HISTORY"

    day_only = [det(2 + 3 * i, 2.0, dn="D") for i in range(10)]
    switched = behaviour_rule(features(day_only + [det(0, 2.0, dn="N")]))
    assert switched["rule"] == "B3_UNMATCHED_HISTORY"
    assert any("other groups (N20/D)" in r for r in switched["reasons"])
    other_satellite = [det(2 + 3 * i, 2.0, sat="N21") for i in range(10)]
    assert behaviour_rule(features(other_satellite + [det(0, 2.0)]))["rule"] == (
        "B3_UNMATCHED_HISTORY"
    )

    partial = [Coverage(date(2026, 3, 7), date(2026, 4, 6), None)]
    gap = behaviour_rule(features(nightly([2.0] * 8) + [det(0, 2.0)], runs=partial))
    assert gap["label"] == "INSUFFICIENT_HISTORY" and gap["rule"] == "B1_LOW_COVERAGE"

    quiet = behaviour_rule(features([det(0, 2.0)]))
    assert quiet["label"] == "NEW_OR_TRANSIENT" and "cloud" in quiet["reasons"][0]
    assert behaviour_rule(features([det(0, None)]))["rule"] == "B0_NO_CURRENT_FRP"


def context(candidates=(), land=None, available=True, nearby=0):
    return {
        "facility_context_available": available,
        "facility_context_note": "No OSM snapshot had been retrieved by this time.",
        "candidates_in_support": list(candidates),
        "nearby_industrial": nearby,
        "land_cover_support": None
        if land is None
        else {"fractions": [{"class": k, "fraction": v} for k, v in land.items()]},
    }


def feature(tag, ftype):
    return {"facility_type": ftype, "primary_tag": tag, "osm_type": "way", "osm_id": 1}


RECURRENT = features(nightly([2.0, 2.1, 1.9, 2.2, 2.0, 1.8]) + [det(0, 2.0)])
QUIET = features([det(0, 2.0)])


@pytest.mark.parametrize(
    ("ctx", "feats", "label", "detail"),
    [
        (context([feature("man_made=flare", "UNKNOWN")], {"BUILT_UP": 0.6}), QUIET,
         "INDUSTRIAL", "GAS_FLARE"),
        (context([feature("landuse=quarry", "MINE")], {"TREE_COVER": 0.9}), RECURRENT,
         "INDUSTRIAL", "MINING_HEAT"),
        (context([feature("power=plant", "POWER")], {"BUILT_UP": 0.3}), RECURRENT,
         "INDUSTRIAL", "OTHER_PERSISTENT_HEAT"),
        (context([feature("power=plant", "POWER")], {"BUILT_UP": 0.3}), QUIET,
         "INDUSTRIAL", "UNRESOLVED"),
        (context([feature("landuse=industrial", "UNKNOWN")], {"CROPLAND": 0.9}), QUIET,
         "UNKNOWN", "WEAK_INDUSTRIAL_SUPPORT"),
        (context([], {"CROPLAND": 0.9}, nearby=2), QUIET, "AGRICULTURAL_BURN", None),
        (context([], {"CROPLAND": 0.9}), RECURRENT, "UNKNOWN", "CONFLICTING_OR_MIXED_EVIDENCE"),
        (context([], {"TREE_COVER": 0.4, "GRASSLAND": 0.3}), QUIET, "VEGETATION_FIRE", None),
        (context([], {"CROPLAND": 0.4, "BUILT_UP": 0.3}, nearby=1), QUIET, "UNKNOWN",
         "CONFLICTING_OR_MIXED_EVIDENCE"),
        (context([], None), QUIET, "UNKNOWN", "LAND_COVER_UNAVAILABLE"),
        (context(available=False), QUIET, "UNKNOWN", "CONTEXT_UNAVAILABLE_AS_OF"),
    ],
)  # fmt: skip
def test_source_rules_abstain_instead_of_forcing_a_class(ctx, feats, label, detail):
    result = source_rule(ctx, feats)
    assert result["label"] == label
    assert detail == (result.get("subtype") or result.get("reason_code"))
    assert result["reasons"]


@pytest.mark.parametrize(
    ("source", "behaviour", "expected"),
    [
        ("INDUSTRIAL", {"label": "ABNORMAL_RELATIVE_TO_BASELINE", "direction": "HIGHER"}, "HIGH"),
        ("INDUSTRIAL", {"label": "NEW_OR_TRANSIENT"}, "HIGH"),
        ("UNKNOWN", {"label": "ABNORMAL_RELATIVE_TO_BASELINE", "direction": "HIGHER"}, "REVIEW"),
        ("UNKNOWN", {"label": "NEW_OR_TRANSIENT"}, "REVIEW"),
        ("INDUSTRIAL", {"label": "INSUFFICIENT_HISTORY"}, "MEDIUM"),
        ("UNKNOWN", {"label": "RECURRENT_WITHIN_BASELINE"}, "MEDIUM"),
        ("INDUSTRIAL", {"label": "ABNORMAL_RELATIVE_TO_BASELINE", "direction": "LOWER"}, "LOW"),
        ("INDUSTRIAL", {"label": "RECURRENT_WITHIN_BASELINE"}, "LOW"),
        ("AGRICULTURAL_BURN", {"label": "NEW_OR_TRANSIENT"}, "LOW"),
    ],
)
def test_priority_is_ordered_and_never_hides_persistent_sites(source, behaviour, expected):
    result = priority_rule({"label": source}, behaviour)
    assert result["label"] == expected
    if (source, behaviour["label"]) == ("INDUSTRIAL", "RECURRENT_WITHIN_BASELINE"):
        assert "not suppressed" in result["note"]


def keys(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from keys(v)
    elif isinstance(value, list):
        for v in value:
            yield from keys(v)


def test_output_is_rules_not_probability_and_hash_is_deterministic():
    detections = nightly([2.0, 2.1, 1.9, 2.2, 2.0, 1.8]) + [det(0, 2.0), det(-2, 50.0)]
    ctx = context([feature("power=plant", "POWER")], {"BUILT_UP": 0.3})
    first = assess(detections, FULL, ctx, AS_OF, Basis.RETROSPECTIVE)
    again = assess(list(reversed(detections)), FULL, ctx, AS_OF, Basis.RETROSPECTIVE)
    assert first["method"] == "RULES" and "Not a trained model" in first["not_a_model"]
    assert not [k for k in keys(first) if "probab" in k.lower()]
    assert first["thresholds"]["status"] == "UNCALIBRATED_DEFAULTS"
    assert first["feature_snapshot_sha256"] == again["feature_snapshot_sha256"]
    assert first["features"]["excluded_after_as_of"] == 1  # the later 50 MW spike is unseen
    assert first["behaviour"]["label"] == "RECURRENT_WITHIN_BASELINE"
    assert any("Retrospective" in note for note in first["missing_or_limited"])
