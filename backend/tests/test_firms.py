import io
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError

import pytest
from thermoscope.config import DataMode
from thermoscope.firms import IngestError, fetch_csv, parse_csv
from thermoscope.regions import Bounds, Window

HEADER = (
    "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,"
    "confidence,version,bright_ti5,frp,daynight\n"
)
ROW = "22.3,69.8,310,0.4,0.5,2026-01-02,905,N20,VIIRS,n,2.0NRT,295,0,D\n"
RECEIVED = datetime(2026, 1, 3, tzinfo=UTC)


def fixture_csv(*rows):
    return (HEADER + "".join(rows or [ROW])).encode()


def window():
    return Window(bounds=Bounds.parse("69.5,22,70.5,23"), start_date="2026-01-01", days=3)


def test_viirs_units_time_and_unknown_historical_availability():
    valid, rejected = parse_csv(fixture_csv(), window(), DataMode.HISTORICAL_REPLAY, RECEIVED)
    assert not rejected
    obs = valid[0].observation
    assert obs.frp_mw == 0 and obs.brightness_i4_k == 310 and obs.brightness_i5_k == 295
    assert obs.scan_km == 0.4 and obs.track_km == 0.5 and obs.source_confidence == "n"
    assert obs.times.acquired_at == datetime(2026, 1, 2, 9, 5, tzinfo=UTC)
    assert obs.times.first_available_at is None
    assert obs.times.source_published_at is None
    assert not obs.times.eligible_as_of(RECEIVED)


@pytest.mark.parametrize(
    "bad",
    [
        ROW.replace("22.3", "91"),
        ROW.replace("69.8", "71.5"),
        ROW.replace(",0,D", ",-1,D"),
        ROW.replace(",0,D", ",NaN,D"),
        ROW.replace(",n,", ",95,"),
        ROW.replace("905", "2400"),
        ROW.replace("2026-01-02", "2026-01-05"),
        ROW.replace("VIIRS", "MODIS"),
        ROW.replace("N20", "N21"),
        ROW.rstrip() + ",extra\n",
    ],
)
def test_bad_row_does_not_discard_valid_neighbours(bad):
    valid, rejected = parse_csv(
        fixture_csv(ROW, bad, ROW), window(), DataMode.SYNTHETIC_FIXTURE, RECEIVED
    )
    assert len(valid) == 2 and len(rejected) == 1
    assert rejected[0].number == 3


def test_missing_values_are_not_zero_and_fetch_time_is_not_acquisition():
    valid, _ = parse_csv(fixture_csv(ROW.replace(",0,D", ",,D")), window(), DataMode.LIVE, RECEIVED)
    assert valid[0].observation.frp_mw is None
    assert valid[0].observation.times.first_available_at == RECEIVED
    assert valid[0].observation.times.first_available_at != valid[0].observation.times.acquired_at


def test_missing_extra_column_is_quarantined_without_crashing_run():
    payload = (HEADER.rstrip() + ",extra\n" + ROW.rstrip() + ",present\n" + ROW).encode()
    valid, rejected = parse_csv(payload, window(), DataMode.HISTORICAL_REPLAY, RECEIVED)
    assert len(valid) == 1 and len(rejected) == 1
    assert rejected[0].number == 3


def test_identity_is_stable_across_formatting_and_modes_but_revision_is_detectable():
    baseline = parse_csv(fixture_csv(), window(), DataMode.LIVE, RECEIVED)[0][0]
    reformatted = parse_csv(
        fixture_csv(ROW.replace("69.8", "69.8000")), window(), DataMode.HISTORICAL_REPLAY, RECEIVED
    )[0][0]
    revision = parse_csv(
        fixture_csv(ROW.replace(",0,D", ",5,D")), window(), DataMode.LIVE, RECEIVED
    )[0][0]
    synthetic = parse_csv(fixture_csv(), window(), DataMode.SYNTHETIC_FIXTURE, RECEIVED)[0][0]
    assert baseline.identity == reformatted.identity == revision.identity
    assert baseline.payload_hash == reformatted.payload_hash != revision.payload_hash
    assert synthetic.identity != baseline.identity


@pytest.mark.parametrize("payload", [b"Invalid MAP_KEY", b"latitude,longitude\n1,2\n", b"\xff"])
def test_non_csv_or_wrong_schema_is_not_an_empty_success(payload):
    with pytest.raises(IngestError):
        parse_csv(payload, window(), DataMode.LIVE, RECEIVED)


class Response(io.BytesIO):
    status = 200


class Opener:
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.calls = 0

    def open(self, request, timeout):
        self.calls += 1
        outcome = next(self.outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return Response(outcome)


def test_provider_retries_are_bounded_and_sanitized():
    secret = "a" * 32
    opener = Opener([URLError("secret:" + secret)] * 3)
    pauses = []
    with pytest.raises(IngestError) as caught:
        fetch_csv(secret, window(), opener=opener, sleep=pauses.append)
    assert opener.calls == 3 and pauses == [1, 2]
    assert secret not in str(caught.value)
    assert caught.value.code == "PROVIDER_UNAVAILABLE"


def test_redirect_is_not_followed_or_retried():
    opener = Opener([HTTPError("withheld", 302, "redirect", {}, None)])
    with pytest.raises(IngestError):
        fetch_csv("a" * 32, window(), opener=opener)
    assert opener.calls == 1


def test_success_after_transient_error_and_credential_echo_rejected():
    opener = Opener([TimeoutError(), fixture_csv()])
    assert fetch_csv("a" * 32, window(), opener=opener, sleep=lambda _: None) == fixture_csv()
    with pytest.raises(IngestError, match="UNSAFE_PROVIDER_RESPONSE"):
        fetch_csv("a" * 32, window(), opener=Opener([b"a" * 32]))


def test_standard_product_keeps_nasa_type_only_as_a_retrospective_field():
    header = HEADER.rstrip("\n") + ",type\n"
    sp_window = Window(
        product="VIIRS_NOAA20_SP", bounds=Bounds.parse("69.5,22,70.5,23"),
        start_date="2026-01-01", days=3,
    )  # fmt: skip
    rows = [ROW.rstrip("\n").replace("2.0NRT", "2") + ",2\n", ROW.rstrip("\n") + ",9\n"]
    valid, rejected = parse_csv((header + "".join(rows)).encode(), sp_window,
                                DataMode.HISTORICAL_REPLAY, RECEIVED)  # fmt: skip
    assert [r.payload["nasa_type"] for r in valid] == [2]
    assert [r.reason for r in rejected] == ["INVALID_VIIRS_ROW"]
    nrt = parse_csv(fixture_csv(), window(), DataMode.HISTORICAL_REPLAY, RECEIVED)[0][0]
    assert "nasa_type" not in nrt.payload  # NRT identity and payload are unchanged
    assert valid[0].identity != nrt.identity  # different product, different physical identity
