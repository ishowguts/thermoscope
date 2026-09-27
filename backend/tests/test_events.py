import random
from datetime import UTC, datetime, timedelta

from thermoscope.events import (
    Distances,
    Params,
    Point,
    build_events,
    build_sites,
    lineage,
    membership_id,
)

T0 = datetime(2026, 1, 2, 9, tzinfo=UTC)


def on_a_line(positions: dict[str, float], limit=1500.0) -> Distances:
    """Synthetic metre positions along one axis; pairs beyond the limit are unknown/far."""
    names = sorted(positions)
    return Distances(
        {
            (a, b): abs(positions[a] - positions[b])
            for i, a in enumerate(names)
            for b in names[i + 1 :]
            if abs(positions[a] - positions[b]) <= limit
        }
    )


def members(groups):
    return sorted(sorted(g.members) for g in groups)


def test_neighbouring_sources_stay_separate_when_interleaved_in_time():
    points = [
        Point("a1", T0),
        Point("b1", T0 + timedelta(hours=1)),
        Point("a2", T0 + timedelta(hours=12)),
        Point("b2", T0 + timedelta(hours=13)),
    ]
    dist = on_a_line({"a1": 0, "a2": 40, "b1": 1000, "b2": 1030})
    groups, merges = build_events(points, dist, Params())
    assert members(groups) == [["a1", "a2"], ["b1", "b2"]] and merges == 0


def test_chain_linking_stops_at_the_maximum_diameter():
    points = [Point(n, T0 + timedelta(hours=i)) for i, n in enumerate(["a", "p", "q", "b"])]
    dist = on_a_line({"a": 0, "p": 700, "q": 1400, "b": 1600})
    groups, _ = build_events(points, dist, Params())
    assert members(groups) == [["a", "p", "q"], ["b"]]
    # "b" linked to q but would stretch the event past 1500 m; that is recorded, not hidden.
    assert next(g for g in groups if g.members == ["b"]).ambiguous == 1


def test_bridging_observation_merges_when_the_result_stays_compact():
    points = [Point("a", T0), Point("b", T0 + timedelta(hours=1)), Point("m", T0 + timedelta(2))]
    dist = on_a_line({"a": 0, "b": 1000, "m": 500})
    groups, merges = build_events(points, dist, Params(max_gap_hours=72))
    assert members(groups) == [["a", "b", "m"]] and merges == 1


def test_time_gap_splits_events_but_the_site_recurs_and_order_does_not_matter():
    points = [
        Point("x1", T0),
        Point("x2", T0 + timedelta(hours=30)),
        Point("far", T0 + timedelta(hours=31)),
    ]
    dist = on_a_line({"x1": 0, "x2": 60, "far": 5000})
    groups, _ = build_events(points, dist, Params())
    shuffled = points[:]
    random.Random(4).shuffle(shuffled)
    assert members(groups) == members(build_events(shuffled, dist, Params())[0])
    assert members(groups) == [["far"], ["x1"], ["x2"]]
    events = [{"id": g.members[0], "members": g.members, "started_at": g.key[0]} for g in groups]
    sites = build_sites(events, dist, Params())
    assert sorted(sorted(e["id"] for e in s["events"]) for s in sites) == [["far"], ["x1", "x2"]]
    assert next(s for s in sites if len(s["events"]) == 2)["anchor"] == "x1"


def test_identity_depends_only_on_membership_and_parameters():
    params = Params().sha256()
    assert membership_id("event", params, ["a", "b"]) == membership_id("event", params, ["a", "b"])
    assert membership_id("event", params, ["a", "b"]) != membership_id("site", params, ["a", "b"])
    assert membership_id("event", params, ["a"]) != membership_id(
        "event", Params(link_distance_m=500).sha256(), ["a"]
    )


def test_lineage_relations():
    old = {"o1": {"a", "b"}, "o2": {"c"}, "o3": {"d", "e"}, "o4": {"f"}, "o5": {"g", "h"}}
    new = {"n1": {"a", "b", "c"}, "n2": {"d"}, "n3": {"e"}, "n4": {"f", "z"}, "n5": {"g", "h"}}
    relations = {(n, o): r for n, o, r, _ in lineage(new, old)}
    assert relations == {
        ("n1", "o1"): "MERGED",
        ("n1", "o2"): "MERGED",
        ("n2", "o3"): "SPLIT",
        ("n3", "o3"): "SPLIT",
        ("n4", "o4"): "GREW",
        ("n5", "o5"): "SAME",
    }
    assert lineage({"n": {"a"}}, {"o": {"a", "b"}}) == [("n", "o", "SHRANK", 1)]
