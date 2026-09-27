"""P05 against a real disposable PostGIS database: registry import, frozen case set, blind
review workflow with adjudication, features, and training that refuses to report without
reviewed test labels."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from test_events_db import load, row
from thermoscope.config import DataMode, Settings
from thermoscope.database import database_engine
from thermoscope.firms import IngestError
from thermoscope.labels import (
    build_case_set,
    case_set_fingerprint,
    grouping_audit,
    import_gppd,
    label_summary,
)
from thermoscope.main import create_app
from thermoscope.ml import compute_case_features, train_and_evaluate

pytestmark = pytest.mark.integration

TOKEN = "fixture-review-token"
URL = "https://worldview.earthdata.nasa.gov/?v=69.5,22.2,69.7,22.4&t=2026-01-02"
IMAGERY = {"url": URL, "kind": "DATED_IMAGERY", "observed_on": "2026-01-02",
           "licence": "NASA EOSDIS open data"}  # fmt: skip
GPPD_CSV = (
    b"country,country_long,name,gppd_idnr,capacity_mw,latitude,longitude,primary_fuel,"
    b"commissioning_year\n"
    b"IND,India,Fixture Coal Station,IND0000001,500,22.3,69.6005,Coal,2010\n"
    b"IND,India,Fixture Solar Park,IND0000002,50,22.3,69.65,Solar,2019\n"
    b"PAK,Pakistan,Elsewhere,PAK0000001,10,22.3,69.7,Coal,2000\n"
)


@pytest.fixture
def configured(test_database, tmp_path):
    command.upgrade(Config("alembic.ini"), "head")
    return Settings(object_store_local_path=tmp_path / "objects", firms_map_key=None,
                    annotation_token=TOKEN)  # fmt: skip


def twelve_sites():
    """Twelve places 5 km apart (separate site groups); every other one seen twice."""
    rows = []
    for k in range(12):
        lon = round(69.6 + 0.05 * k, 4)
        rows.append(row(22.3, lon, 2, "2100", 3.0 + k))
        if k % 2 == 0:
            rows.append(row(22.3, round(lon + 0.0005, 4), 2, "0905", 1.0))
    return rows


def test_case_set_reviews_features_and_training_gate(configured):
    assert load(configured, *twelve_sites())["status"] == "SUCCEEDED"

    sha = hashlib.sha256(GPPD_CSV).hexdigest()
    at = datetime(2026, 9, 27, tzinfo=UTC)
    assert import_gppd(configured, GPPD_CSV, sha, at)["records"] == 1  # Indian thermal only
    assert import_gppd(configured, GPPD_CSV, sha, at)["records"] == 1  # same file: idempotent
    changed = GPPD_CSV.replace(b"500", b"600")
    with pytest.raises(IngestError, match="REGISTRY_VERSION_CONFLICT"):
        import_gppd(configured, changed, hashlib.sha256(changed).hexdigest(), at)
    with pytest.raises(IngestError, match="FILE_HASH_MISMATCH"):
        import_gppd(configured, GPPD_CSV, "0" * 64, at)

    # The original grouping is kept as a frozen set; a facility-aware set supersedes it with a
    # recorded reason before any review exists.
    old = build_case_set(configured, "fixture-v1", DataMode.SYNTHETIC_FIXTURE,
                         grouping="site-2km-v1")  # fmt: skip
    with pytest.raises(IngestError, match="SUPERSEDING_NEEDS_A_REASON"):
        build_case_set(configured, "fixture-set", DataMode.SYNTHETIC_FIXTURE,
                       supersedes="fixture-v1")  # fmt: skip
    built = build_case_set(
        configured,
        "fixture-set",
        DataMode.SYNTHETIC_FIXTURE,
        supersedes="fixture-v1",
        reason="facility-aware grouping (test)",
    )
    assert built["grouping"] == "facility-aware-v1"  # fmt: skip
    assert built["cases"] == 12 and built["site_groups"] == 12
    before = case_set_fingerprint(configured, "fixture-v1")
    after = case_set_fingerprint(configured, "fixture-set")
    assert before["episode_ids_sha256"] == after["episode_ids_sha256"]  # same episodes
    assert before["case_set"]["manifest_sha256"] == old["manifest_sha256"]  # v1 untouched
    assert grouping_audit(configured, "fixture-set")["safe_for_unseen_site_claims"]
    assert set(built["splits"]) == {"TRAIN", "VALIDATION", "TEST"}
    manifest = (configured.object_store_local_path / "manifests" /
                f"case-set-{built['case_set_id']}.json").read_bytes()  # fmt: skip
    assert hashlib.sha256(manifest.rstrip(b"\n")).hexdigest() == built["manifest_sha256"]
    with pytest.raises(IngestError, match="CASE_SET_EXISTS"):
        build_case_set(configured, "fixture-set", DataMode.SYNTHETIC_FIXTURE)

    features = compute_case_features(configured, "fixture-set")
    assert features["cases"] == 12 and features["silver_labels"] == 1  # the coal station
    assert features["history_complete"] == 0  # one fixture day: no 90-day history anywhere
    again = compute_case_features(configured, "fixture-set")
    assert again["cases"] == 0 and again["unchanged"] == 12  # stored version reused, not rewritten

    client = TestClient(create_app(configured))
    base = "/api/v1/annotation/fixture-set"
    sets = client.get("/api/v1/annotation/case-sets").json()
    assert sets["review_enabled"] and sets["case_sets"][0]["name"] == "fixture-set"
    assert sets["case_sets"][1]["superseded_by"] == "fixture-set"

    queue = client.get(f"{base}/queue", params={"reviewer": "Asha"}).json()
    first = queue["review"][0]
    assert first["split"] == "TEST" and first["needs"] == 2
    case_id = first["case_id"]

    case = client.get(f"{base}/cases/{case_id}")
    assert case.status_code == 200
    blind = case.json()
    assert blind["blind"] and blind["adjudication"] is None
    for hidden in ("weak", "silver", "rule", "p_industrial", "probability", "score"):
        assert hidden not in case.text.lower(), hidden
    assert blind["links"][0]["url"].startswith("https://worldview.earthdata.nasa.gov/")

    def post(who, label, evidence=(IMAGERY,), token=TOKEN, where=base):
        payload = {"case_id": case_id, "reviewer": who, "source_label": label,
                   "certainty": "MEDIUM", "source_location": "INSIDE_PIXEL_AREA",
                   "evidence": list(evidence)}  # fmt: skip
        return client.post(f"{where}/reviews", json=payload,
                           headers={"X-Annotation-Token": token})  # fmt: skip

    superseded = post("Asha", "INDUSTRIAL", where="/api/v1/annotation/fixture-v1")
    assert superseded.status_code == 409 and superseded.json()["code"] == "CASE_SET_SUPERSEDED"
    assert post("Asha", "INDUSTRIAL", token="wrong").status_code == 401
    mismatch = post("Asha", "INDUSTRIAL", evidence=(IMAGERY | {"observed_on": "2026-01-01"},))
    assert mismatch.status_code == 422  # imagery date must match the Worldview link
    first_review = post("Asha", "INDUSTRIAL").json()
    assert first_review["role"] == "REVIEWER" and first_review["independent_evidence"]
    assert post("asha", "OTHER").status_code == 422  # same person, any case
    assert post("Ben", "AGRICULTURAL_BURN").json()["role"] == "REVIEWER"

    # Second reviewer never saw the first; the disagreement goes to an adjudicator.
    chen = client.get(f"{base}/queue", params={"reviewer": "Chen"}).json()
    assert [i["case_id"] for i in chen["adjudication"]] == [case_id]
    detail = client.get(f"{base}/cases/{case_id}").json()["adjudication"]
    assert detail["needed"] and len(detail["earlier_reviews"]) == 2
    assert "reviewer" not in json.dumps(detail["earlier_reviews"])
    assert post("Chen", "AGRICULTURAL_BURN").json()["role"] == "ADJUDICATOR"
    assert post("Dev", "INDUSTRIAL").status_code == 422  # nothing left to review

    summary = label_summary(configured, "fixture-set")
    assert summary["gold_test_labels"] == {"AGRICULTURAL_BURN": 1}
    assert summary["double_reviewed_cases"] == 1 and summary["pending_adjudication"] == 0
    assert summary["kappa_pairs"] == 1  # "cannot decide" pairs would be left out

    with database_engine(configured) as engine, engine.connect() as conn:
        stored = conn.execute(
            text("SELECT role,blind,evidence FROM label_reviews ORDER BY reviewed_at")
        ).all()
    assert [r.role for r in stored] == ["REVIEWER", "REVIEWER", "ADJUDICATOR"]
    assert all(r.blind for r in stored)
    assert stored[0].evidence["policy"] == "evidence-policy-v1"
    assert stored[0].evidence["items"][0]["licence"] == "NASA EOSDIS open data"
    assert stored[0].evidence["source_location"] == "INSIDE_PIXEL_AREA"

    # Frozen splits and append-only reviews are enforced by the database, not only the app.
    for statement in (
        "UPDATE label_cases SET split='TRAIN' WHERE split='TEST'",
        "DELETE FROM label_reviews",
        "UPDATE label_reviews SET source_label='INDUSTRIAL'",
        "TRUNCATE label_reviews CASCADE",
        "DELETE FROM case_sets",
        "UPDATE case_features SET weak_label=NULL",
    ):
        with pytest.raises(DBAPIError, match="immutable"):
            with database_engine(configured) as engine, engine.begin() as conn:
                conn.execute(text(statement))
    with pytest.raises(IntegrityError):  # one review per person per case, any letter case
        with database_engine(configured) as engine, engine.begin() as conn:
            conn.execute(
                text("""INSERT INTO label_reviews (id,case_set_id,case_id,reviewer,role,
                    source_label,certainty,evidence,blind,reviewed_at)
                    SELECT gen_random_uuid(),case_set_id,case_id,'ASHA','ADJUDICATOR',
                        'OTHER','LOW','{}'::jsonb,true,now() FROM label_reviews LIMIT 1""")
            )
    assert (
        case_set_fingerprint(configured, "fixture-set")["splits_sha256"] == (after["splits_sha256"])
    )

    with pytest.raises(ValueError, match="superseded"):
        train_and_evaluate(configured, "fixture-v1")
    reviewed = train_and_evaluate(configured, "fixture-set")
    assert reviewed["status"] == "INSUFFICIENT_LABELS"
    out = Path(reviewed["artifact_dir"])
    assert out.parent == configured.object_store_local_path.parent / "models"
    assert {p.name for p in out.iterdir()} == {"metrics.json", "model_card.md", "manifest.json"}
    assert "No evaluation" in (out / "model_card.md").read_text()
    metrics = json.loads((out / "metrics.json").read_text())
    assert metrics["history_policy"]["cases_eligible"] == 0  # every fixture case set aside
    assert metrics["protocols"]["held-out-region-v1"] == "NOT_RUN"
    dry = train_and_evaluate(configured, "fixture-set", dry_run_weak=True)
    assert dry["status"] == "DRY_RUN_NOT_EVIDENCE"
    models = client.get("/api/v1/models").json()["models"]
    assert {m["status"] for m in models} == {"INSUFFICIENT_LABELS", "DRY_RUN_NOT_EVIDENCE"}
