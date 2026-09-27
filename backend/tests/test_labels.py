"""P05 label integrity: frozen group splits, blind review ordering, tiering and validation."""

import pytest
from fastapi.testclient import TestClient
from thermoscope.config import Settings
from thermoscope.labels import (
    assign_splits,
    cohen_kappa,
    eligible_for_test,
    resolve_label,
    review_order,
    submit_review,
    union_groups,
)
from thermoscope.main import create_app

URL = "https://worldview.earthdata.nasa.gov/?v=1,2,3,4"


def review(label, role="REVIEWER", evidence=(URL,), who="a"):
    return {"source_label": label, "role": role, "evidence": list(evidence), "reviewer": who}


def cases(region, groups):
    return [
        {"id": f"{region}-{g}-{i}", "region_id": region, "split_group": f"{region}-{g}"}
        for g, n in groups.items()
        for i in range(n)
    ]


def test_union_groups_chains_close_sites_and_keeps_far_sites_apart():
    groups = union_groups(["a", "b", "c", "d"], [("a", "b"), ("b", "c")])
    assert groups == {"a": "a", "b": "a", "c": "a", "d": "d"}


def test_splits_never_divide_a_site_group_and_follow_case_shares():
    items = cases("r1", {f"g{i}": 1 + i % 4 for i in range(40)}) + cases(
        "r2", {"x": 3, "y": 2, "z": 1}
    )
    splits = assign_splits(items)
    for c in items:
        c["split"] = splits[c["split_group"]]
    by_group = {}
    for c in items:
        by_group.setdefault(c["split_group"], set()).add(c["split"])
    assert all(len(v) == 1 for v in by_group.values())
    r1 = [c for c in items if c["region_id"] == "r1"]
    share = {s: sum(c["split"] == s for c in r1) / len(r1) for s in ("TRAIN", "VALIDATION", "TEST")}
    assert 0.5 <= share["TRAIN"] <= 0.7 and 0.1 <= share["TEST"] <= 0.3
    # A small region with three groups still contributes to every split.
    assert {splits[g] for g in ("r2-x", "r2-y", "r2-z")} == {"TRAIN", "VALIDATION", "TEST"}
    assert assign_splits(list(reversed(items))) == splits  # order-independent


def test_review_order_interleaves_splits_regions_and_groups():
    items = cases("a", {"g1": 3, "g2": 3, "g3": 2}) + cases("b", {"h1": 2, "h2": 2})
    split_of = {"a-g1": "TEST", "a-g2": "TRAIN", "a-g3": "VALIDATION", "b-h1": "TEST",
                "b-h2": "TRAIN"}  # fmt: skip
    for c in items:
        c["split"] = split_of[c["split_group"]]
    order = review_order(items)
    assert len(order) == len(items) == len(set(order))
    splits = {c["id"]: c["split"] for c in items}
    # A handful of reviews already reaches every split, test first.
    assert [splits[i] for i in order[:3]] == ["TEST", "TRAIN", "VALIDATION"]
    tests = [i for i in order if splits[i] == "TEST"]
    assert tests[0].split("-")[0] != tests[1].split("-")[0]  # regions take turns
    assert review_order(list(reversed(items))) == order


def test_tiers_gold_needs_evidence_and_test_needs_two_agreeing_reviews():
    one = resolve_label([review("INDUSTRIAL")], 1, None, None)
    assert one == {"label": "INDUSTRIAL", "tier": "GOLD", "basis": "ONE_REVIEWER"}
    assert not eligible_for_test(one)
    half = resolve_label([review("INDUSTRIAL")], 2, None, None)
    assert half["tier"] == "SILVER" and not eligible_for_test(half)
    agree = resolve_label([review("INDUSTRIAL"), review("INDUSTRIAL", who="b")], 2, None, None)
    assert agree["basis"] == "TWO_REVIEWERS_AGREE" and eligible_for_test(agree)
    uncited = resolve_label(
        [review("OTHER", evidence=()), review("OTHER", evidence=(), who="b")], 2, None, None
    )
    assert uncited["tier"] == "SILVER" and not eligible_for_test(uncited)
    split = [review("INDUSTRIAL"), review("AGRICULTURAL_BURN", who="b")]
    assert resolve_label(split, 2, "INDUSTRIAL", "INDUSTRIAL")["basis"] == (
        "DISAGREEMENT_PENDING_ADJUDICATION"
    )
    settled = resolve_label(split + [review("AGRICULTURAL_BURN", "ADJUDICATOR", who="c")], 2,
                            None, None)  # fmt: skip
    assert settled["label"] == "AGRICULTURAL_BURN" and eligible_for_test(settled)
    unsure = resolve_label([review("UNRESOLVED", evidence=())], 1, "INDUSTRIAL", None)
    assert unsure["tier"] == "UNRESOLVED"  # a human "cannot decide" beats registry evidence


def test_registry_and_rules_never_become_gold():
    silver = resolve_label([], 2, "INDUSTRIAL", "AGRICULTURAL_BURN")
    assert silver == {"label": "INDUSTRIAL", "tier": "SILVER", "basis": "REGISTRY_CORROBORATED"}
    weak = resolve_label([], 2, None, "AGRICULTURAL_BURN")
    assert weak["tier"] == "WEAK" and not eligible_for_test(weak)
    assert resolve_label([], 1, None, "UNKNOWN")["tier"] is None


def test_kappa():
    assert cohen_kappa([]) is None
    assert cohen_kappa([("IND", "IND"), ("NON", "NON")]) == 1.0
    assert cohen_kappa([("IND", "NON"), ("NON", "IND")]) == -1.0
    assert cohen_kappa([("IND", "IND"), ("IND", "IND")]) is None  # no variation


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"reviewer": "x"}, "reviewer"),
        ({"reviewer": "Asha", "source_label": "FIRE", "certainty": "HIGH"}, "source label"),
        (
            {
                "reviewer": "Asha",
                "source_label": "OTHER",
                "certainty": "HIGH",
                "industrial_subtype": "GAS_FLARE",
                "evidence": [URL],
            },
            "subtype",
        ),  # fmt: skip
        (
            {
                "reviewer": "Asha",
                "source_label": "OTHER",
                "certainty": "HIGH",
                "evidence": ["javascript:alert(1)"],
            },
            "links",
        ),  # fmt: skip
        ({"reviewer": "Asha", "source_label": "OTHER", "certainty": "HIGH"}, "evidence link"),
    ],
)
def test_submit_review_validates_before_touching_the_database(payload, message):
    settings = Settings(_env_file=None, database_url=None)
    with pytest.raises(ValueError, match=message):
        submit_review(settings, "any", payload | {"case_id": "0" * 64})


def body():
    return {"case_id": "a" * 64, "reviewer": "Asha", "source_label": "INDUSTRIAL",
            "certainty": "HIGH", "evidence": [URL]}  # fmt: skip


def test_review_submission_is_disabled_without_a_token():
    client = TestClient(create_app(Settings(_env_file=None, database_url=None)))
    response = client.post("/api/v1/annotation/pilot-set/reviews", json=body())
    assert response.status_code == 503
    assert response.json()["code"] == "ANNOTATION_DISABLED"


def test_review_submission_rejects_a_wrong_token_and_bad_bodies():
    settings = Settings(_env_file=None, database_url=None, annotation_token="correct-token")
    client = TestClient(create_app(settings))
    url = "/api/v1/annotation/pilot-set/reviews"
    wrong = client.post(url, json=body(), headers={"X-Annotation-Token": "nope"})
    assert wrong.status_code == 401 and "correct-token" not in wrong.text
    assert client.post(url, json=body()).status_code == 401
    bad = client.post(url, json=body() | {"source_label": "FIRE"},
                      headers={"X-Annotation-Token": "correct-token"})  # fmt: skip
    assert bad.status_code == 422
    extra = client.post(url, json=body() | {"model_score": 0.9},
                        headers={"X-Annotation-Token": "correct-token"})  # fmt: skip
    assert extra.status_code == 422


def test_cors_allows_review_posts_from_the_workbench_only():
    client = TestClient(create_app(Settings(_env_file=None, database_url=None)))
    headers = {"Access-Control-Request-Method": "POST",
               "Access-Control-Request-Headers": "content-type,x-annotation-token"}  # fmt: skip
    ok = client.options("/api/v1/annotation/pilot-set/reviews",
                        headers=headers | {"Origin": "http://127.0.0.1:5173"})  # fmt: skip
    assert ok.status_code == 200
    assert "x-annotation-token" in ok.headers["access-control-allow-headers"].lower()
    other = client.options("/api/v1/annotation/pilot-set/reviews",
                           headers=headers | {"Origin": "https://example.org"})  # fmt: skip
    assert other.status_code == 400
