"""P05 label integrity: frozen group splits, blind review ordering, tiering and validation."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from thermoscope.config import Settings
from thermoscope.labels import (
    assess_evidence,
    assign_splits,
    cohen_kappa,
    eligible_for_test,
    forced_kind,
    resolve_label,
    review_order,
    submit_review,
    union_groups,
)
from thermoscope.main import create_app
from thermoscope.reviewers import TOKEN, _issue, bearer_token, token_sha256

URL = "https://worldview.earthdata.nasa.gov/?v=1,2,3,4&t=2026-05-01"
START = datetime(2026, 5, 1, 8, tzinfo=UTC)
IMAGERY = {"url": URL, "kind": "DATED_IMAGERY", "observed_on": "2026-05-01"}
OSM_LINK = {"url": "https://www.openstreetmap.org/way/1", "kind": "PROJECT_INPUT"}


def review(label, role="REVIEWER", evidence=(IMAGERY,), who="a", certainty="HIGH",
           location="INSIDE_PIXEL_AREA"):  # fmt: skip
    checked = assess_evidence(list(evidence), START, START) | {"source_location": location}
    return {"source_label": label, "role": role, "reviewer": who, "certainty": certainty,
            "evidence": checked}  # fmt: skip


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
    # Citing ThermoScope's own inputs is not independent evidence.
    circular = resolve_label(
        [
            review("INDUSTRIAL", evidence=(OSM_LINK,)),
            review("INDUSTRIAL", evidence=(OSM_LINK,), who="b"),
        ],
        2,
        None,
        None,
    )
    assert circular["tier"] == "SILVER" and not eligible_for_test(circular)
    # Ambiguity stays out of test truth: a LOW-certainty agreement is not GOLD.
    doubtful = resolve_label(
        [review("INDUSTRIAL"), review("INDUSTRIAL", who="b", certainty="LOW")], 2, None, None
    )
    assert doubtful["tier"] == "SILVER"
    # A source seen only near the pixel area leaves the label geographically uncertain.
    nearby = resolve_label([review("INDUSTRIAL", location="NEARBY_ONLY")], 1, None, None)
    assert nearby["tier"] == "SILVER"
    half_sure = resolve_label(
        [review("INDUSTRIAL"), review("INDUSTRIAL", who="b", location="UNSURE")], 2, None, None
    )
    assert half_sure["tier"] == "SILVER"  # every agreeing reviewer must place it inside
    legacy = {"source_label": "OTHER", "role": "REVIEWER", "reviewer": "z", "certainty": "HIGH",
              "evidence": [URL]}  # fmt: skip
    assert resolve_label([legacy], 1, None, None)["tier"] == "SILVER"  # unknown format
    split = [review("INDUSTRIAL"), review("AGRICULTURAL_BURN", who="b")]
    assert resolve_label(split, 2, "INDUSTRIAL", "INDUSTRIAL")["basis"] == (
        "DISAGREEMENT_PENDING_ADJUDICATION"
    )
    settled = resolve_label(split + [review("AGRICULTURAL_BURN", "ADJUDICATOR", who="c")], 2,
                            None, None)  # fmt: skip
    assert settled["label"] == "AGRICULTURAL_BURN" and eligible_for_test(settled)
    # With one blind review voided, the adjudication no longer has a disagreement to settle; a
    # later blind review reopens it for a new adjudicator (reviews are in saved order).
    adjudication = review("AGRICULTURAL_BURN", "ADJUDICATOR", who="c")
    alone = resolve_label([split[0], adjudication], 2, None, None)
    assert alone["basis"] == "ONE_OF_TWO_REVIEWS" and not eligible_for_test(alone)
    later = resolve_label([split[0], adjudication, review("OTHER", who="d")], 2, None, None)
    assert later["basis"] == "DISAGREEMENT_PENDING_ADJUDICATION"
    unsure = resolve_label([review("UNRESOLVED", evidence=())], 1, "INDUSTRIAL", None)
    assert unsure["tier"] == "UNRESOLVED"  # a human "cannot decide" beats registry evidence


def test_registry_and_rules_never_become_gold():
    silver = resolve_label([], 2, "INDUSTRIAL", "AGRICULTURAL_BURN")
    assert silver == {"label": "INDUSTRIAL", "tier": "SILVER", "basis": "REGISTRY_CORROBORATED"}
    weak = resolve_label([], 2, None, "AGRICULTURAL_BURN")
    assert weak["tier"] == "WEAK" and not eligible_for_test(weak)
    assert resolve_label([], 1, None, "UNKNOWN")["tier"] is None


def test_evidence_policy_is_decided_by_the_server():
    assert forced_kind("https://www.openstreetmap.org/way/1") == "PROJECT_INPUT"
    assert forced_kind("https://firms.modaps.eosdis.nasa.gov/map/") == "PROJECT_INPUT"
    assert forced_kind("https://github.com/wri/global-power-plant-database") == "PROJECT_INPUT"
    assert forced_kind("https://www.google.com/maps/@22.3,69.8,1200m") == "UNDATED_BASEMAP"
    assert forced_kind("https://www.google.com/search?q=refinery") is None
    assert forced_kind(URL) is None
    for trick in (
        "https://www.openstreetmap.org./way/1",
        "https://firms2.modaps.eosdis.nasa.gov/",
        "https://overpass-turbo.eu/?Q=x",
        "https://maps.mail.ru/osm/tools/overpass/api",
        "https://raw.githubusercontent.com/wri/global-power-plant-database/x.csv",
    ):
        assert forced_kind(trick) == "PROJECT_INPUT", trick
    for basemap in ("https://maps.app.goo.gl/abc", "https://www.arcgis.com/apps/mapviewer"):
        assert forced_kind(basemap) == "UNDATED_BASEMAP", basemap
    assert forced_kind("https://openstreetmap.org.example.com/x") is None  # not the real host
    with pytest.raises(ValueError, match="date"):
        assess_evidence(
            [
                {
                    "url": "https://worldview.earthdata.nasa.gov/?v=1,2,3,4",
                    "kind": "DATED_IMAGERY",
                    "observed_on": "2026-05-01",
                }
            ],
            START,
            START,
        )
    thermal_only = URL + "&l=VIIRS_NOAA20_Thermal_Anomalies_375m_All"
    with pytest.raises(ValueError, match="thermal"):
        assess_evidence([IMAGERY | {"url": thermal_only}], START, START)
    both = URL + "&l=VIIRS_NOAA20_CorrectedReflectance_TrueColor,VIIRS_NOAA20_Thermal_Anomalies"
    assert assess_evidence([IMAGERY | {"url": both}], START, START)["independent"]
    with pytest.raises(ValueError, match="PROJECT_INPUT"):
        assess_evidence([{"url": OSM_LINK["url"], "kind": "DATED_IMAGERY",
                          "observed_on": "2026-05-01"}], START, START)  # fmt: skip
    with pytest.raises(ValueError, match="imagery date"):
        assess_evidence([{"url": URL, "kind": "DATED_IMAGERY"}], START, START)
    with pytest.raises(ValueError, match="match the date"):
        assess_evidence([IMAGERY | {"observed_on": "2026-04-30"}], START, START)
    old_image = {"url": "https://example.org/s2.png", "kind": "DATED_IMAGERY",
                 "observed_on": "2024-01-01"}  # fmt: skip
    assert not assess_evidence([old_image], START, START)["independent"]
    news = {"url": "https://example.org/news", "kind": "NEWS_REPORT"}
    assert not assess_evidence([news], START, START)["independent"]
    report = {"url": "https://example.org/annual-report.pdf", "kind": "OFFICIAL_OR_COMPANY",
              "licence": "link only"}  # fmt: skip
    checked = assess_evidence([news, report], START, START)
    assert checked["independent"] and checked["claim_scope"] == "SOURCE_IDENTITY_ONLY"
    assert checked["items"][1]["verification"] == "REVIEWER_ATTESTED"  # recorded, not checked
    official = {"url": "https://cpcb.nic.in/report.pdf", "kind": "OFFICIAL_OR_COMPANY"}
    assert assess_evidence([official], START, START)["items"][0]["verification"] == (
        "OFFICIAL_DOMAIN"
    )
    assert assess_evidence([IMAGERY], START, START)["independent"]
    assert not assess_evidence([IMAGERY], None, None)["independent"]  # form check only


def test_kappa():
    assert cohen_kappa([]) is None
    assert cohen_kappa([("IND", "IND"), ("NON", "NON")]) == 1.0
    assert cohen_kappa([("IND", "NON"), ("NON", "IND")]) == -1.0
    assert cohen_kappa([("IND", "IND"), ("IND", "IND")]) is None  # no variation


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"source_label": "INDUSTRIAL"}, "certainty"),
        ({"source_label": "FIRE", "certainty": "HIGH"}, "source label"),
        (
            {
                "source_label": "OTHER",
                "certainty": "HIGH",
                "industrial_subtype": "GAS_FLARE",
                "evidence": [IMAGERY],
            },
            "subtype",
        ),  # fmt: skip
        (
            {
                "source_label": "OTHER",
                "certainty": "HIGH",
                "evidence": [{"url": "javascript:alert(1)", "kind": "OTHER"}],
            },
            "links",
        ),  # fmt: skip
        ({"source_label": "OTHER", "certainty": "HIGH"}, "evidence link"),
        (
            {
                "source_label": "OTHER",
                "certainty": "HIGH",
                "evidence": [IMAGERY],
            },
            "pixel area",
        ),  # fmt: skip
        (
            {
                "source_label": "OTHER",
                "certainty": "HIGH",
                "source_location": "NEARBY_ONLY",
                "evidence": [IMAGERY],
            },
            "expected_role",
        ),  # fmt: skip
        (
            {
                "source_label": "OTHER",
                "certainty": "HIGH",
                "evidence": [{"url": URL}],
            },
            "evidence type",
        ),  # fmt: skip
    ],
)
def test_submit_review_validates_before_touching_the_database(payload, message):
    settings = Settings(_env_file=None, database_url=None)
    with pytest.raises(ValueError, match=message):
        submit_review(settings, "any", payload | {"case_id": "0" * 64}, ACCOUNT)


ACCOUNT = {"id": "00000000-0000-0000-0000-000000000001", "name": "Asha", "can_adjudicate": False}
WELL_FORMED = "tsr_" + "A" * 43


def body():
    return {"case_id": "a" * 64, "source_label": "INDUSTRIAL", "certainty": "HIGH",
            "source_location": "INSIDE_PIXEL_AREA", "evidence": [IMAGERY],
            "expected_role": "REVIEWER"}  # fmt: skip


def test_bearer_token_accepts_only_the_personal_token_format():
    assert bearer_token(f"Bearer {WELL_FORMED}") == WELL_FORMED
    assert bearer_token(f"bearer  {WELL_FORMED} ") == WELL_FORMED
    for header in (None, "", WELL_FORMED, f"Basic {WELL_FORMED}", "Bearer shared-secret",
                   f"Bearer {WELL_FORMED}x", "Bearer tsr_short"):  # fmt: skip
        assert bearer_token(header) is None, header
    token, digest = _issue()
    assert TOKEN.fullmatch(token) and digest == token_sha256(token) and token not in digest


def test_review_endpoints_require_a_personal_sign_in():
    client = TestClient(create_app(Settings(_env_file=None, database_url=None)))
    base = "/api/v1/annotation/pilot-set"
    requests = [
        ("get", "/api/v1/annotation/me", None),
        ("get", f"{base}/queue", None),
        ("get", f"{base}/cases/{'a' * 64}", None),
        ("post", f"{base}/reviews", body()),
    ]
    for method, url, payload in requests:
        for headers in ({}, {"Authorization": "Bearer shared-secret"},
                        {"X-Annotation-Token": WELL_FORMED}):  # fmt: skip
            response = client.request(method, url, json=payload, headers=headers)
            assert response.status_code == 401, (url, headers)
            assert response.json()["code"] == "UNAUTHORIZED"
        # A well-formed token needs the account database; without it the API says so (503).
        signed = client.request(method, url, json=payload,
                                headers={"Authorization": f"Bearer {WELL_FORMED}"})  # fmt: skip
        assert signed.status_code == 503 and WELL_FORMED not in signed.text


def test_review_bodies_are_validated_and_cannot_name_a_reviewer():
    client = TestClient(create_app(Settings(_env_file=None, database_url=None)))
    url = "/api/v1/annotation/pilot-set/reviews"
    headers = {"Authorization": f"Bearer {WELL_FORMED}"}
    for bad in (
        body() | {"reviewer": "Somebody Else"},  # identity comes from the account only
        {k: v for k, v in body().items() if k != "expected_role"},  # role shown must be sent
        body() | {"expected_role": "OWNER"},
        body() | {"source_label": "FIRE"},
        body() | {"model_score": 0.9},
        body() | {"evidence": [URL]},  # a bare link without a type is no longer accepted
        body() | {"evidence": [IMAGERY | {"independent": True}]},  # clients cannot claim it
    ):
        assert client.post(url, json=bad, headers=headers).status_code == 422


def test_review_only_server_withholds_automated_assessments():
    client = TestClient(create_app(Settings(_env_file=None, database_url=None, review_only=True)))
    oid = "0" * 64
    for path in (f"/api/v1/observations/{oid}/assessment", f"/api/v1/observations/{oid}/timeline"):
        response = client.get(path)
        assert response.status_code == 403
        assert response.json()["code"] == "WITHHELD_ON_REVIEW_SERVER"
    assert client.get("/api/v1/status").json()["review_only"] is True
    # Label progress (tiers, agreement, pending adjudications) would tell a second reviewer
    # whether they agreed with the first: it has no HTTP endpoint at all (owners run
    # `make ml ARGS="summary ..."`).
    for server in (client, TestClient(create_app(Settings(_env_file=None, database_url=None)))):
        assert server.get("/api/v1/annotation/pilot-set/summary").status_code == 404


def test_cors_allows_review_posts_from_the_workbench_only():
    client = TestClient(create_app(Settings(_env_file=None, database_url=None)))
    headers = {"Access-Control-Request-Method": "POST",
               "Access-Control-Request-Headers": "content-type,authorization"}  # fmt: skip
    ok = client.options("/api/v1/annotation/pilot-set/reviews",
                        headers=headers | {"Origin": "http://127.0.0.1:5173"})  # fmt: skip
    assert ok.status_code == 200
    assert "authorization" in ok.headers["access-control-allow-headers"].lower()
    other = client.options("/api/v1/annotation/pilot-set/reviews",
                           headers=headers | {"Origin": "https://example.org"})  # fmt: skip
    assert other.status_code == 400
