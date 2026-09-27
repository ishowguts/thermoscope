"""Bounded OpenStreetMap context from Overpass: fixed query, allowed hosts, tag-based typing.

Facility type is a deterministic reading of OSM tags. It proposes what a mapped feature is;
it is not an independent label, and a missing feature is not evidence that no industry exists.
"""

import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener

from thermoscope.firms import IngestError, NoRedirect
from thermoscope.regions import Bounds

PROVIDER = "OSM_OVERPASS"
QUERY_VERSION = "osm-industrial-v1"
TYPE_MAP_VERSION = "facility-type-v1"
LICENSE = "ODbL-1.0"
ATTRIBUTION = "© OpenStreetMap contributors, ODbL 1.0"
# Only these hosts are ever contacted; the second is a public mirror used when the first is busy.
OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
)
MAX_BYTES = 32_000_000
MAX_ELEMENTS = 20_000
FACILITY_TYPES = (
    "REFINERY",
    "PETROCHEMICAL",
    "STEEL",
    "POWER",
    "LNG",
    "MINE",
    "OTHER",
    "UNKNOWN",
)
_MAN_MADE = "works|flare|chimney|kiln|petroleum_well|mineshaft|gasometer"
_RENEWABLE = "wind|solar|hydro"


def build_query(bounds: Bounds) -> str:
    """Exact query text; its hash is recorded so a saved response can be tied to it."""
    box = ",".join(f"{v:g}" for v in (bounds.south, bounds.west, bounds.north, bounds.east))
    return (
        f"[out:json][timeout:90][maxsize:67108864][bbox:{box}];\n"
        "(\n"
        'nwr["landuse"="industrial"];\n'
        'nwr["industrial"];\n'
        f'nwr["man_made"~"^({_MAN_MADE})$"];\n'
        f'nwr["power"="plant"]["plant:source"!~"^({_RENEWABLE})$"];\n'
        f'nwr["power"="generator"]["generator:source"!~"^({_RENEWABLE})$"];\n'
        'nwr["landuse"="quarry"];\n'
        ");\n"
        "out meta geom;\n"
    )


def fetch_overpass(
    query: str, *, opener=None, sleep=time.sleep, endpoints=OVERPASS_ENDPOINTS
) -> tuple[bytes, str]:
    client = opener if opener is not None else build_opener(NoRedirect())
    body = urlencode({"data": query}).encode()
    code = "PROVIDER_UNAVAILABLE"
    for endpoint in endpoints:
        if endpoint not in OVERPASS_ENDPOINTS:
            raise IngestError("ENDPOINT_NOT_ALLOWED")
        for attempt in range(2):
            request = Request(
                endpoint,
                data=body,
                headers={"User-Agent": "ThermoScope/0.3 OSM regional context pilot (SIH26162)"},
            )
            retry = False
            try:
                with client.open(request, timeout=120) as response:
                    if response.status != 200:
                        raise IngestError("PROVIDER_HTTP_ERROR")
                    payload = response.read(MAX_BYTES + 1)
                if len(payload) > MAX_BYTES:
                    raise IngestError("RESPONSE_TOO_LARGE")
                validate_payload(payload)
                return payload, endpoint
            except HTTPError as error:
                code = "PROVIDER_RATE_LIMITED" if error.code == 429 else "PROVIDER_HTTP_ERROR"
                retry = error.code in {429, 500, 502, 503, 504}
                error.close()
            except (TimeoutError, URLError, OSError):
                code, retry = "PROVIDER_UNAVAILABLE", True
            except IngestError as error:
                # An incomplete or malformed Overpass answer can succeed on another server.
                code, retry = error.code, error.code == "OVERPASS_INCOMPLETE"
            if not retry:
                raise IngestError(code) from None  # A rejected query fails on every server.
            if attempt == 0:
                sleep(2)
    raise IngestError(code) from None


def validate_payload(payload: bytes) -> dict:
    """Overpass can return HTTP 200 with a runtime error remark; never store that as complete."""
    try:
        document = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise IngestError("MALFORMED_OVERPASS_JSON") from None
    if not isinstance(document, dict) or not isinstance(document.get("elements"), list):
        raise IngestError("MALFORMED_OVERPASS_JSON")
    remark = document.get("remark")
    if isinstance(remark, str) and ("error" in remark.lower() or "timed out" in remark.lower()):
        raise IngestError("OVERPASS_INCOMPLETE")
    base = (document.get("osm3s") or {}).get("timestamp_osm_base")
    if not isinstance(base, str):
        raise IngestError("OSM_BASE_TIMESTAMP_MISSING")
    try:
        parse_time(base)
    except ValueError:
        raise IngestError("OSM_BASE_TIMESTAMP_MISSING") from None
    if len(document["elements"]) > MAX_ELEMENTS:
        raise IngestError("ELEMENT_LIMIT_EXCEEDED")
    return document


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp without zone")
    return parsed.astimezone(UTC)


def _value(tags: dict, key: str) -> str:
    return str(tags.get(key, "")).strip().lower()


def facility_type(tags: dict) -> str:
    """First matching rule wins; order puts the most specific evidence first."""
    industrial, man_made = _value(tags, "industrial"), _value(tags, "man_made")
    power = _value(tags, "power")
    product = _value(tags, "product")
    carried = {industrial, product, _value(tags, "content"), _value(tags, "substance")}
    if "lng" in carried or industrial in {"lng", "lng_terminal"}:
        return "LNG"
    if industrial in {"refinery", "oil_refinery", "oil"} or (
        man_made == "works" and product in {"oil", "petroleum", "petrol", "diesel"}
    ):
        return "REFINERY"
    if industrial in {"chemical", "petrochemical"}:
        return "PETROCHEMICAL"
    if industrial in {"steel", "steelmaking", "steelworks", "iron_works", "metallurgy"} or (
        product in {"steel", "iron"}
    ):
        return "STEEL"
    if power in {"plant", "generator"}:
        return "POWER"
    if (
        _value(tags, "landuse") == "quarry"
        or industrial in {"mine", "mining", "quarry"}
        or man_made == "mineshaft"
    ):
        return "MINE"
    if (industrial and industrial not in {"yes"}) or man_made == "kiln":
        return "OTHER"
    return "UNKNOWN"


def primary_tag(tags: dict) -> str:
    for key in ("man_made", "power", "industrial", "landuse"):
        if key in tags:
            return f"{key}={tags[key]}"
    return "unknown"


@dataclass
class Facility:
    osm_type: str
    osm_id: int
    osm_version: int | None
    osm_timestamp: datetime | None
    name: str | None
    facility_type: str
    primary_tag: str
    tags: dict
    geometry: dict  # GeoJSON; relations arrive as member lines and become areas in PostGIS
    build: str  # POINT, WAY_POLYGON or RELATION_AREA


@dataclass
class RejectedElement:
    osm_type: str
    osm_id: int
    reason: str


def _ring(points) -> list[list[float]]:
    coordinates = []
    for point in points:
        lon, lat = float(point["lon"]), float(point["lat"])
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise ValueError("coordinate outside range")
        coordinates.append([lon, lat])
    return coordinates


def _geometry(element: dict) -> tuple[dict, str]:
    kind = element["type"]
    if kind == "node":
        (point,) = _ring([element])
        return {"type": "Point", "coordinates": point}, "POINT"
    if kind == "way":
        line = _ring(element.get("geometry") or [])
        if len(line) >= 4 and line[0] == line[-1]:
            return {"type": "Polygon", "coordinates": [line]}, "WAY_POLYGON"
        raise ValueError("UNCLOSED_AREA_WAY")
    if (element.get("tags") or {}).get("type") not in {"multipolygon", "boundary"}:
        raise ValueError("UNSUPPORTED_RELATION_TYPE")
    lines = []
    for member in element.get("members") or []:
        if member.get("type") != "way" or member.get("role") not in {"outer", "inner", ""}:
            continue
        if not member.get("geometry"):
            raise ValueError("INCOMPLETE_RELATION_GEOMETRY")
        lines.append(_ring(member["geometry"]))
    if not lines:
        raise ValueError("INCOMPLETE_RELATION_GEOMETRY")
    return {"type": "MultiLineString", "coordinates": lines}, "RELATION_AREA"


def parse_overpass(payload: bytes) -> tuple[datetime, list[Facility], list[RejectedElement]]:
    document = validate_payload(payload)
    osm_base = parse_time(document["osm3s"]["timestamp_osm_base"])
    facilities, rejected, seen = [], [], set()
    for element in document["elements"]:
        kind, osm_id = element.get("type"), element.get("id")
        if kind not in {"node", "way", "relation"} or not isinstance(osm_id, int):
            rejected.append(RejectedElement(str(kind), int(osm_id or 0), "UNSUPPORTED_ELEMENT"))
            continue
        if (kind, osm_id) in seen:
            continue  # One element can match several query clauses; keep one copy.
        seen.add((kind, osm_id))
        tags = {str(k): str(v) for k, v in (element.get("tags") or {}).items()}
        try:
            geometry, build = _geometry(element)
            stamp = element.get("timestamp")
            facilities.append(
                Facility(
                    osm_type=kind,
                    osm_id=osm_id,
                    osm_version=element.get("version"),
                    osm_timestamp=parse_time(stamp) if isinstance(stamp, str) else None,
                    name=tags.get("name:en") or tags.get("name"),
                    facility_type=facility_type(tags),
                    primary_tag=primary_tag(tags),
                    tags=tags,
                    geometry=geometry,
                    build=build,
                )
            )
        except (KeyError, TypeError, ValueError) as error:
            reason = str(error) if str(error).isupper() else "INVALID_GEOMETRY"
            rejected.append(RejectedElement(kind, osm_id, reason))
    facilities.sort(key=lambda f: (f.osm_type, f.osm_id))
    return osm_base, facilities, rejected
