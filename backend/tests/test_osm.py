import io
import json
from urllib.error import HTTPError, URLError

import pytest
from thermoscope.context import (
    GEOLOCATION_BUFFER_M,
    NOMINAL_VIIRS_I_KM,
    summarize,
    support_radius_m,
)
from thermoscope.firms import IngestError
from thermoscope.osm import (
    OVERPASS_ENDPOINTS,
    build_query,
    facility_type,
    fetch_overpass,
    parse_overpass,
    validate_payload,
)
from thermoscope.regions import Bounds

BASE = "2026-01-05T00:00:00Z"


def overpass(*elements, base=BASE, remark=None):
    document = {"version": 0.6, "osm3s": {"timestamp_osm_base": base}, "elements": list(elements)}
    if remark:
        document["remark"] = remark
    return json.dumps(document).encode()


def square(lon, lat, size=0.01):
    ring = [(lon, lat), (lon + size, lat), (lon + size, lat + size), (lon, lat + size), (lon, lat)]
    return [{"lon": x, "lat": y} for x, y in ring]


def way(osm_id, points, **tags):
    return {"type": "way", "id": osm_id, "version": 3, "timestamp": BASE, "tags": tags,
            "geometry": points}  # fmt: skip


def test_query_is_bounded_deterministic_and_excludes_renewables():
    bounds = Bounds.parse("69.5,22,70.5,23")
    query = build_query(bounds)
    assert query == build_query(Bounds.parse("69.5,22,70.5,23"))
    assert "[bbox:22,69.5,23,70.5]" in query and "out meta geom;" in query
    assert '["generator:source"!~"^(wind|solar|hydro)$"]' in query
    assert "[timeout:90]" in query and "[maxsize:67108864]" in query


@pytest.mark.parametrize(
    ("tags", "expected"),
    [
        ({"industrial": "refinery"}, "REFINERY"),
        ({"man_made": "works", "product": "oil"}, "REFINERY"),
        ({"industrial": "chemical"}, "PETROCHEMICAL"),
        ({"industrial": "steelmaking"}, "STEEL"),
        ({"power": "plant", "plant:source": "coal"}, "POWER"),
        ({"power": "generator"}, "POWER"),
        ({"industrial": "lng"}, "LNG"),
        ({"man_made": "storage_tank", "content": "LNG"}, "LNG"),
        ({"landuse": "quarry"}, "MINE"),
        ({"man_made": "kiln"}, "OTHER"),
        ({"industrial": "brickyard"}, "OTHER"),
        ({"landuse": "industrial"}, "UNKNOWN"),
        ({"landuse": "industrial", "industrial": "yes"}, "UNKNOWN"),
        ({"man_made": "flare"}, "UNKNOWN"),
    ],
)
def test_tag_based_facility_types(tags, expected):
    assert facility_type(tags) == expected


def test_parse_points_areas_relations_and_rejections():
    relation = {
        "type": "relation",
        "id": 7,
        "tags": {"type": "multipolygon", "industrial": "refinery", "name": "Test refinery"},
        "members": [
            {"type": "way", "ref": 1, "role": "outer", "geometry": square(69.8, 22.3, 0.02)},
            {"type": "way", "ref": 2, "role": "inner", "geometry": square(69.805, 22.305, 0.005)},
            {"type": "node", "ref": 9, "role": "", "lat": 22.31, "lon": 69.81},
        ],
    }
    payload = overpass(
        {"type": "node", "id": 5, "lat": 22.31, "lon": 69.81, "tags": {"man_made": "flare"}},
        way(10, square(69.9, 22.4), landuse="industrial"),
        way(10, square(69.9, 22.4), landuse="industrial"),  # matched by two query clauses
        way(11, square(69.9, 22.4)[:3], landuse="industrial"),  # unclosed area
        relation,
        {"type": "relation", "id": 8, "tags": {"type": "site"}, "members": []},
        {
            "type": "relation",
            "id": 12,
            "tags": {"type": "multipolygon", "landuse": "industrial"},
            "members": [{"type": "way", "ref": 3, "role": "outer"}],
        },
    )
    base, facilities, rejected = parse_overpass(payload)
    assert base.isoformat() == "2026-01-05T00:00:00+00:00"
    assert [(f.osm_type, f.osm_id, f.build) for f in facilities] == [
        ("node", 5, "POINT"),
        ("relation", 7, "RELATION_AREA"),
        ("way", 10, "WAY_POLYGON"),
    ]
    assert facilities[1].facility_type == "REFINERY" and facilities[1].name == "Test refinery"
    assert len(facilities[1].geometry["coordinates"]) == 2  # outer and inner lines only
    assert {(r.osm_type, r.osm_id, r.reason) for r in rejected} == {
        ("way", 11, "UNCLOSED_AREA_WAY"),
        ("relation", 8, "UNSUPPORTED_RELATION_TYPE"),
        ("relation", 12, "INCOMPLETE_RELATION_GEOMETRY"),
    }


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (b"<html>busy</html>", "MALFORMED_OVERPASS_JSON"),
        (overpass(remark='runtime error: Query timed out in "query"'), "OVERPASS_INCOMPLETE"),
        (json.dumps({"elements": []}).encode(), "OSM_BASE_TIMESTAMP_MISSING"),
        (overpass(base="yesterday"), "OSM_BASE_TIMESTAMP_MISSING"),
    ],
)
def test_incomplete_or_malformed_answers_are_never_complete(payload, code):
    with pytest.raises(IngestError) as caught:
        validate_payload(payload)
    assert caught.value.code == code


class Response(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class Opener:
    def __init__(self, outcomes):
        self.outcomes, self.urls = list(outcomes), []

    def open(self, request, timeout):
        self.urls.append(request.full_url)
        assert request.data.startswith(b"data=") and timeout == 120
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return Response(outcome)


def busy(code=504):
    return HTTPError("https://example.invalid", code, "busy", {}, io.BytesIO())


def test_busy_primary_falls_back_to_the_allowed_mirror():
    opener = Opener([busy(), busy(), overpass()])
    payload, endpoint = fetch_overpass("q", opener=opener, sleep=lambda _: None)
    assert endpoint == OVERPASS_ENDPOINTS[1] and payload == overpass()
    assert opener.urls == [OVERPASS_ENDPOINTS[0], OVERPASS_ENDPOINTS[0], OVERPASS_ENDPOINTS[1]]


def test_incomplete_answer_is_retried_elsewhere_and_failures_stay_sanitized():
    opener = Opener([overpass(remark="runtime error: out of memory"), overpass(base=BASE)])
    assert fetch_overpass("q", opener=opener, sleep=lambda _: None)[1] == OVERPASS_ENDPOINTS[0]
    with pytest.raises(IngestError) as caught:
        fetch_overpass("q", opener=Opener([URLError("secret detail")] * 4), sleep=lambda _: None)
    assert caught.value.code == "PROVIDER_UNAVAILABLE" and "secret" not in str(caught.value)
    with pytest.raises(IngestError) as caught:
        fetch_overpass("q", opener=Opener([busy(400)]), sleep=lambda _: None)
    assert caught.value.code == "PROVIDER_HTTP_ERROR"
    with pytest.raises(IngestError) as caught:
        fetch_overpass("q", endpoints=("https://example.invalid/api",), sleep=lambda _: None)
    assert caught.value.code == "ENDPOINT_NOT_ALLOWED"


def test_support_radius_uses_pixel_size_or_labelled_nominal_size():
    radius, basis = support_radius_m(0.4, 0.5)
    assert basis == "SCAN_TRACK"
    assert radius == pytest.approx(320.156 + GEOLOCATION_BUFFER_M, abs=0.01)
    nominal, basis = support_radius_m(None, 0.5)
    assert basis == "NOMINAL_VIIRS_I_BAND"
    assert nominal == pytest.approx(500 * NOMINAL_VIIRS_I_KM * 2**0.5 + GEOLOCATION_BUFFER_M)


def test_association_summary_keeps_ambiguity_and_missing_coverage_distinct():
    inside, near = {"relation": "INSIDE_SUPPORT"}, {"relation": "NEARBY"}
    assert summarize([], covered=False) == "CONTEXT_NOT_COVERED"
    assert summarize([], covered=True) == "NO_MAPPED_FEATURE_NEARBY"
    assert summarize([near], covered=True) == "NEARBY_ONLY"
    assert summarize([inside, near], covered=True) == "SINGLE_MAPPED_FEATURE"
    assert summarize([inside, inside], covered=True) == "MULTIPLE_MAPPED_FEATURES"
