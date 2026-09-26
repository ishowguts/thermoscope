from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from thermoscope.contracts import SourceTimes, ThermalObservation


def times(**changes):
    values = dict(
        acquired_at="2026-01-01T05:00:00+05:30",
        first_available_at="2026-01-01T00:00:00Z",
        ingested_at="2026-01-01T01:00:00Z",
        availability_evidence="KNOWN",
    )
    return SourceTimes(**(values | changes))


def observation(**changes):
    return ThermalObservation(
        **(
            dict(
                provider="synthetic-test",
                product="fixture",
                sensor="VIIRS",
                satellite="fixture",
                longitude=70,
                latitude=22.5,
                frp_mw=0,
                brightness_i4_k=320,
                source_confidence="n",
                data_mode="SYNTHETIC_FIXTURE",
                times=times(),
                raw_sha256="0" * 64,
            )
            | changes
        )
    )


def test_utc_normalization_crosses_date_boundary():
    assert times().acquired_at == datetime(2025, 12, 31, 23, 30, tzinfo=UTC)


def test_replay_excludes_data_not_available_yet():
    assert not times().eligible_as_of(datetime(2025, 12, 31, 23, 45, tzinfo=UTC))
    assert times().eligible_as_of(datetime(2026, 1, 1, 0, 0, tzinfo=UTC))


def test_unknown_availability_cannot_certify_operational_replay():
    uncertain = times(first_available_at=None, availability_evidence="UNKNOWN")
    assert not uncertain.eligible_as_of(datetime(2026, 2, 1, tzinfo=UTC))


@pytest.mark.parametrize(
    "changes",
    [
        {"acquired_at": "2026-01-01T05:00:00"},
        {"ingested_at": "2025-01-01T00:00:00Z"},
        {"first_available_at": "2026-02-01T00:00:00Z"},
        {"first_available_at": None},
        {"availability_evidence": "UNKNOWN"},
    ],
)
def test_invalid_time_claims_are_rejected(changes):
    with pytest.raises(ValidationError):
        times(**changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"latitude": 91},
        {"longitude": 181},
        {"frp_mw": -1},
        {"frp_mw": float("nan")},
        {"brightness_i4_k": 0},
        {"source_confidence": 0.95},
        {"brightness_modis_k": 300},
        {"sensor": "MODIS", "brightness_i4_k": None, "source_confidence": "n"},
    ],
)
def test_invalid_sensor_values_are_rejected(changes):
    with pytest.raises(ValidationError):
        observation(**changes)


def test_zero_and_missing_frp_remain_distinct():
    assert observation().frp_mw == 0
    assert observation(frp_mw=None).frp_mw is None
