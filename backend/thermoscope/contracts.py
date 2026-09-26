from datetime import UTC, datetime
from enum import StrEnum

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from thermoscope.config import DataMode


class AvailabilityEvidence(StrEnum):
    KNOWN = "KNOWN"
    UNKNOWN = "UNKNOWN"


class SourceTimes(BaseModel):
    model_config = ConfigDict(extra="forbid")
    acquired_at: AwareDatetime
    source_published_at: AwareDatetime | None = None
    first_available_at: AwareDatetime | None = None
    ingested_at: AwareDatetime
    availability_evidence: AvailabilityEvidence

    @field_validator("acquired_at", "source_published_at", "first_available_at", "ingested_at")
    @classmethod
    def normalize_utc(cls, value):
        return value.astimezone(UTC) if value is not None else None

    @model_validator(mode="after")
    def validate_order(self):
        if self.ingested_at < self.acquired_at:
            raise ValueError("ingestion cannot precede acquisition")
        for value in (self.source_published_at, self.first_available_at):
            if value is not None and not self.acquired_at <= value <= self.ingested_at:
                raise ValueError(
                    "publication and availability must fall within acquisition/ingestion"
                )
        if self.availability_evidence == AvailabilityEvidence.KNOWN:
            if self.first_available_at is None:
                raise ValueError("known availability requires first_available_at")
        elif self.first_available_at is not None:
            raise ValueError("unknown availability must not invent first_available_at")
        return self

    def eligible_as_of(self, as_of: datetime) -> bool:
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("as_of must include a timezone")
        return (
            self.availability_evidence == AvailabilityEvidence.KNOWN
            and self.first_available_at is not None
            and self.acquired_at <= as_of
            and self.first_available_at <= as_of
        )


class ThermalObservation(BaseModel):
    """Normalized units; source confidence is deliberately not a class probability."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    provider: str = Field(min_length=1)
    product: str = Field(min_length=1)
    sensor: str = Field(pattern="^(VIIRS|MODIS)$")
    satellite: str = Field(min_length=1)
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)
    frp_mw: float | None = Field(default=None, ge=0)
    brightness_i4_k: float | None = Field(default=None, gt=0)
    brightness_i5_k: float | None = Field(default=None, gt=0)
    brightness_modis_k: float | None = Field(default=None, gt=0)
    scan_km: float | None = Field(default=None, gt=0)
    track_km: float | None = Field(default=None, gt=0)
    source_confidence: str | float | None = None
    data_mode: DataMode
    times: SourceTimes
    raw_sha256: str = Field(pattern="^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_sensor(self):
        if self.sensor == "VIIRS":
            if self.source_confidence is not None and self.source_confidence not in {"l", "n", "h"}:
                raise ValueError("VIIRS source confidence must be l, n or h")
            if self.brightness_modis_k is not None:
                raise ValueError("MODIS brightness does not belong to a VIIRS observation")
        else:
            if self.brightness_i4_k is not None or self.brightness_i5_k is not None:
                raise ValueError("VIIRS bands do not belong to a MODIS observation")
            if self.source_confidence is not None:
                if not isinstance(self.source_confidence, (int, float)):
                    raise ValueError("MODIS confidence must be numeric")
                if not 0 <= self.source_confidence <= 100:
                    raise ValueError("MODIS confidence must be between 0 and 100")
        return self
