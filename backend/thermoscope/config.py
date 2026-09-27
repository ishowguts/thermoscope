from enum import StrEnum
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class DataMode(StrEnum):
    LIVE = "LIVE"
    HISTORICAL_REPLAY = "HISTORICAL_REPLAY"
    SYNTHETIC_FIXTURE = "SYNTHETIC_FIXTURE"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)
    database_url: SecretStr | None = None
    firms_map_key: SecretStr | None = None
    # Shared secret for submitting label reviews; reviews are disabled while it is unset.
    annotation_token: SecretStr | None = None
    # A reviewer-facing server: rule assessments and timelines are withheld so blind reviewers
    # cannot look up the automated answer (P05 review integrity).
    review_only: bool = False
    object_store_local_path: Path = Path("local/objects")
    app_data_mode: DataMode = DataMode.SYNTHETIC_FIXTURE
    allowed_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]

    @field_validator("database_url", mode="before")
    @classmethod
    def empty_database_is_unconfigured(cls, value):
        return None if value == "" else value

    @field_validator("database_url")
    @classmethod
    def validate_database_driver(cls, value):
        if value is None:
            return value
        try:
            url = make_url(value.get_secret_value())
            if url.drivername != "postgresql+psycopg" or not url.database or not url.host:
                raise ValueError
        except Exception:
            raise ValueError("DATABASE_URL must be a PostgreSQL psycopg connection URL") from None
        return value
