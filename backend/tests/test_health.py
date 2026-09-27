import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from thermoscope.config import Settings
from thermoscope.main import create_app


def test_liveness_survives_unconfigured_database():
    settings = Settings(_env_file=None, database_url=None)
    with TestClient(create_app(settings)) as client:
        assert client.get("/health/live").status_code == 200
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.json()["checks"]["database"] == "not_configured"
        assert response.json()["request_id"] == response.headers["X-Request-ID"]


def test_unreachable_database_does_not_leak_credentials():
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://test:private-test-password@127.0.0.1:1/test",
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.json()["checks"]["database"] == "unavailable"
        assert "private-test-password" not in response.text
        assert "postgresql" not in response.text


def test_no_invented_classifier_or_observation_count():
    with TestClient(create_app(Settings(_env_file=None, database_url=None))) as client:
        status = client.get("/api/v1/status").json()
        assert status["classifier_status"] == "NOT_SERVED_AWAITING_REVIEWED_LABELS"
        assert status["observation_count"] is None


def test_invalid_configuration_hides_input():
    with pytest.raises(ValidationError) as caught:
        Settings(_env_file=None, database_url="mysql://user:never-print-this@host/db")
    assert "never-print-this" not in str(caught.value)
