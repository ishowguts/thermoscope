"""NASA Area CSV adapter and strict, row-isolated VIIRS normalization."""

import csv
import hashlib
import io
import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from pydantic import ValidationError

from thermoscope.config import DataMode
from thermoscope.contracts import SourceTimes, ThermalObservation
from thermoscope.regions import SATELLITES, Window

MAX_BYTES = 4_000_000
MAX_ROWS = 20_000
REQUIRED_FIELDS = {
    "latitude",
    "longitude",
    "bright_ti4",
    "scan",
    "track",
    "acq_date",
    "acq_time",
    "satellite",
    "instrument",
    "confidence",
    "version",
    "bright_ti5",
    "frp",
    "daynight",
}


class IngestError(Exception):
    """Only safe codes cross the adapter boundary; never retain request exceptions."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_csv(key: str | None, window: Window, *, opener=None, sleep=time.sleep) -> bytes:
    if key is None or not re.fullmatch(r"[A-Za-z0-9]{32}", key):
        raise IngestError("FIRMS_KEY_MISSING_OR_INVALID")
    endpoint = (
        "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        + key
        + "/"
        + window.product.value
        + "/"
        + window.bounds.csv()
        + "/"
        + str(window.days)
        + "/"
        + window.start_date.isoformat()
    )
    request = Request(endpoint, headers={"User-Agent": "ThermoScope/0.2 NASA-FIRMS regional pilot"})
    client = opener if opener is not None else build_opener(NoRedirect())
    code = "PROVIDER_UNAVAILABLE"
    for attempt in range(3):
        retry = False
        try:
            with client.open(request, timeout=20) as response:
                if response.status != 200:
                    raise IngestError("PROVIDER_HTTP_ERROR")
                payload = response.read(MAX_BYTES + 1)
            if len(payload) > MAX_BYTES:
                raise IngestError("RESPONSE_TOO_LARGE")
            if key.encode() in payload:
                raise IngestError("UNSAFE_PROVIDER_RESPONSE")
            return payload
        except HTTPError as error:
            code = "PROVIDER_RATE_LIMITED" if error.code == 429 else "PROVIDER_HTTP_ERROR"
            retry = error.code in {429, 500, 502, 503, 504}
            error.close()
        except (TimeoutError, URLError, OSError):
            code, retry = "PROVIDER_UNAVAILABLE", True
        if not retry or attempt == 2:
            break
        sleep(2**attempt)
    raise IngestError(code) from None


@dataclass
class ParsedRow:
    number: int
    observation: ThermalObservation
    identity: str
    payload_hash: str
    payload: dict
    raw: dict


@dataclass
class RejectedRow:
    number: int
    reason: str
    raw: dict


def digest(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def decimal_coordinate(value: str) -> str:
    number = Decimal(value)
    if not number.is_finite():
        raise ValueError("invalid coordinate")
    return "0" if number == 0 else format(number.normalize(), "f")


def optional_number(value: str | None):
    return None if value is None or value.strip() == "" else float(value)


def parse_csv(payload: bytes, window: Window, mode: DataMode, received_at: datetime):
    if len(payload) > MAX_BYTES:
        raise IngestError("RESPONSE_TOO_LARGE")
    try:
        reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")), strict=True)
        names = reader.fieldnames or []
        if not REQUIRED_FIELDS.issubset(names) or len(names) != len(set(names)):
            raise IngestError("UNSUPPORTED_CSV_SCHEMA")
        raw_rows = list(reader)
    except (UnicodeError, csv.Error):
        raise IngestError("MALFORMED_CSV") from None
    if len(raw_rows) > MAX_ROWS:
        raise IngestError("ROW_LIMIT_EXCEEDED")
    content_hash = hashlib.sha256(payload).hexdigest()
    valid, rejected = [], []
    for number, original in enumerate(raw_rows, start=2):
        raw = {str(k): v for k, v in original.items()}
        try:
            if None in original or any(value is None for value in original.values()):
                raise ValueError("incorrect column count")
            row = {k: v.strip() for k, v in original.items()}
            if row["instrument"] != "VIIRS" or row["satellite"] != SATELLITES[window.product]:
                raise ValueError("sensor/product mismatch")
            if row["daynight"] not in {"D", "N"} or not row["version"]:
                raise ValueError("missing provenance")
            if not re.fullmatch(r"\d{1,4}", row["acq_time"]):
                raise ValueError("invalid acquisition time")
            acquired = datetime.strptime(
                row["acq_date"] + " " + row["acq_time"].zfill(4), "%Y-%m-%d %H%M"
            ).replace(tzinfo=UTC)
            if not window.start_date <= acquired.date() <= window.end_date:
                raise ValueError("date outside requested window")
            times = SourceTimes(
                acquired_at=acquired,
                ingested_at=received_at,
                first_available_at=received_at if mode == DataMode.LIVE else None,
                availability_evidence="KNOWN" if mode == DataMode.LIVE else "UNKNOWN",
            )
            obs = ThermalObservation(
                provider="NASA_FIRMS",
                product=window.product.value,
                sensor="VIIRS",
                satellite=row["satellite"],
                longitude=float(row["longitude"]),
                latitude=float(row["latitude"]),
                frp_mw=optional_number(row["frp"]),
                brightness_i4_k=optional_number(row["bright_ti4"]),
                brightness_i5_k=optional_number(row["bright_ti5"]),
                scan_km=optional_number(row["scan"]),
                track_km=optional_number(row["track"]),
                source_confidence=row["confidence"] or None,
                data_mode=mode,
                times=times,
                raw_sha256=content_hash,
            )
            if not window.bounds.contains(obs.longitude, obs.latitude):
                raise ValueError("coordinate outside requested bounds")
            identity = digest(
                {
                    "version": "firms-identity-v1",
                    "namespace": "fixture" if mode == DataMode.SYNTHETIC_FIXTURE else "nasa",
                    "product": window.product.value,
                    "sensor": "VIIRS",
                    "satellite": obs.satellite,
                    "acquired_at": acquired.isoformat(),
                    "longitude": decimal_coordinate(row["longitude"]),
                    "latitude": decimal_coordinate(row["latitude"]),
                }
            )
            normalized = obs.model_dump(mode="json", exclude={"times", "data_mode", "raw_sha256"})
            normalized.update(
                acquired_at=acquired.isoformat(),
                collection_version=row["version"],
                daynight=row["daynight"],
            )
            if row.get("type", "") != "":
                # Standard products carry NASA's broad source type. It is kept only as a
                # retrospective comparison, never as a label or an operational feature.
                if row["type"] not in {"0", "1", "2", "3"}:
                    raise ValueError("invalid NASA type")
                normalized["nasa_type"] = int(row["type"])
            valid.append(ParsedRow(number, obs, identity, digest(normalized), normalized, raw))
        except (ValueError, TypeError, InvalidOperation, ValidationError):
            # The raw row is preserved privately; no untrusted value enters a public error message.
            rejected.append(RejectedRow(number, "INVALID_VIIRS_ROW", raw))
    return valid, rejected
