"""P05 against a real disposable PostGIS database: registry import, frozen case set, blind
review workflow with personal reviewer accounts and adjudication, features, and training that
refuses to report without reviewed test labels."""

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
from thermoscope.reviewers import (
    add_reviewer,
    deactivate,
    list_reviewers,
    reactivate,
    rotate_token,
    token_sha256,
    void_reviews,
)

pytestmark = pytest.mark.integration

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
    return Settings(object_store_local_path=tmp_path / "objects", firms_map_key=None)


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

    # Feature rows are immutable, so they are not written on a truncated archive by accident.
    with pytest.raises(ValueError, match="HISTORY_ARCHIVE_INCOMPLETE"):
        compute_case_features(configured, "fixture-set")
    features = compute_case_features(configured, "fixture-set", allow_partial_history=True)
    assert features["history_archive"]["regions_short"][0]["region_id"] == "jamnagar"
    assert features["cases"] == 12 and features["silver_labels"] == 1  # the coal station
    assert features["history_complete"] == 0  # one fixture day: no 90-day history anywhere
    again = compute_case_features(configured, "fixture-set", allow_partial_history=True)
    assert again["cases"] == 0 and again["unchanged"] == 12  # stored version reused, not rewritten

    client = TestClient(create_app(configured))
    base = "/api/v1/annotation/fixture-set"
    sets = client.get("/api/v1/annotation/case-sets").json()
    assert not sets["review_enabled"]  # no reviewer accounts yet
    assert sets["case_sets"][0]["name"] == "fixture-set"
    assert sets["case_sets"][1]["superseded_by"] == "fixture-set"

    # Personal accounts: the server keeps only a hash of each token.
    tokens = {}
    for name, adjudicator in (("Asha", False), ("Ben", False), ("Dev", False), ("Chen", True)):
        account, tokens[name] = add_reviewer(configured, name, adjudicator)
        assert account["name"] == name and "token" not in account
    with pytest.raises(ValueError, match="already exists"):
        add_reviewer(configured, "  asha ")
    assert client.get("/api/v1/annotation/case-sets").json()["review_enabled"]

    def auth(who):
        return {"Authorization": f"Bearer {tokens[who]}"}

    me = client.get("/api/v1/annotation/me", headers=auth("Chen")).json()
    assert me == {"name": "Chen", "can_adjudicate": True, "sign_in": "reviewer-accounts-v1"}
    assert client.get(f"{base}/queue").status_code == 401

    queue = client.get(f"{base}/queue", headers=auth("Asha")).json()
    assert queue["reviewer"] == "Asha" and not queue["can_adjudicate"]
    first = queue["review"][0]
    assert first["split"] == "TEST" and first["needs"] == 2
    case_id = first["case_id"]
    case_url = f"{base}/cases/{case_id}"

    assert client.get(case_url).status_code == 401
    case = client.get(case_url, headers=auth("Asha"))
    assert case.status_code == 200
    blind = case.json()
    assert blind["blind"] and blind["adjudication"] is None and not blind["reviewed_by_you"]
    assert blind["your_role"] == "REVIEWER"
    for hidden in ("weak", "silver", "rule", "p_industrial", "probability", "score"):
        assert hidden not in case.text.lower(), hidden
    assert blind["links"][0]["url"].startswith("https://worldview.earthdata.nasa.gov/")

    def post(who, label, evidence=(IMAGERY,), where=base, headers=None, role="REVIEWER"):
        payload = {"case_id": case_id, "source_label": label, "certainty": "MEDIUM",
                   "source_location": "INSIDE_PIXEL_AREA", "evidence": list(evidence),
                   "expected_role": role}  # fmt: skip
        return client.post(f"{where}/reviews", json=payload,
                           headers=auth(who) if headers is None else headers)  # fmt: skip

    superseded = post("Asha", "INDUSTRIAL", where="/api/v1/annotation/fixture-v1")
    assert superseded.status_code == 409 and superseded.json()["code"] == "CASE_SET_SUPERSEDED"
    forged = {"Authorization": "Bearer tsr_" + "B" * 43}
    assert post("Asha", "INDUSTRIAL", headers=forged).status_code == 401
    assert post("Asha", "INDUSTRIAL", headers={}).status_code == 401
    mismatch = post("Asha", "INDUSTRIAL", evidence=(IMAGERY | {"observed_on": "2026-01-01"},))
    assert mismatch.status_code == 422  # imagery date must match the Worldview link
    first_review = post("Asha", "INDUSTRIAL").json()
    assert first_review["role"] == "REVIEWER" and first_review["independent_evidence"]
    assert post("Asha", "OTHER").status_code == 422  # one review per account per case
    assert post("Ben", "AGRICULTURAL_BURN").json()["role"] == "REVIEWER"

    # The disagreement is settled only by an adjudicator account that did not review the case,
    # and only from the adjudication view: a review written blind is refused with the same
    # answer whatever changed, so it neither becomes the deciding label nor reveals the split.
    dev = client.get(f"{base}/queue", headers=auth("Dev")).json()
    assert dev["adjudication"] == [] and dev["remaining_adjudications"] is None
    assert client.get(case_url, headers=auth("Dev")).json()["adjudication"] is None
    for who, role in (("Dev", "REVIEWER"), ("Dev", "ADJUDICATOR"), ("Chen", "REVIEWER")):
        stale = post(who, "OTHER", role=role)
        assert stale.status_code == 409 and stale.json()["code"] == "CASE_CHANGED", (who, role)
    asha_queue = client.get(f"{base}/queue", headers=auth("Asha")).json()
    assert asha_queue["your_reviews"] == 1 and asha_queue["remaining_adjudications"] is None
    asha_view = client.get(case_url, headers=auth("Asha")).json()
    assert asha_view["adjudication"] is None and asha_view["reviewed_by_you"]
    chen = client.get(f"{base}/queue", headers=auth("Chen")).json()
    assert [i["case_id"] for i in chen["adjudication"]] == [case_id]
    chen_view = client.get(case_url, headers=auth("Chen")).json()
    assert chen_view["your_role"] == "ADJUDICATOR"
    detail = chen_view["adjudication"]
    assert detail["needed"] and len(detail["earlier_reviews"]) == 2
    assert "reviewer" not in json.dumps(detail["earlier_reviews"])
    assert "Asha" not in json.dumps(detail) and "Ben" not in json.dumps(detail)
    assert post("Chen", "AGRICULTURAL_BURN", role="ADJUDICATOR").json()["role"] == "ADJUDICATOR"
    assert post("Dev", "INDUSTRIAL").status_code == 409  # nothing left to review

    # Rotation replaces a token; deactivation locks the account out; accounts are listed with
    # their review counts, never their tokens.
    old = tokens["Ben"]
    tokens["Ben"] = rotate_token(configured, "ben")
    with pytest.raises(LookupError):
        reactivate(configured, "Ben")  # still active: nothing to reopen
    assert client.get("/api/v1/annotation/me",
                      headers={"Authorization": f"Bearer {old}"}).status_code == 401  # fmt: skip
    assert client.get("/api/v1/annotation/me", headers=auth("Ben")).status_code == 200
    deactivate(configured, "Ben")
    assert client.get("/api/v1/annotation/me", headers=auth("Ben")).status_code == 401
    with pytest.raises(LookupError):
        deactivate(configured, "Nobody")
    with pytest.raises(LookupError):
        rotate_token(configured, "Ben")  # a closed account is reopened, not silently rotated
    tokens["Ben"] = reactivate(configured, "Ben")
    assert client.get("/api/v1/annotation/me", headers=auth("Ben")).status_code == 200
    deactivate(configured, "Ben")
    listed = list_reviewers(configured)
    assert {r["name"]: (r["reviews"], r["active"]) for r in listed} == {
        "Asha": (1, True), "Ben": (1, False), "Chen": (1, True), "Dev": (0, True),
    }  # fmt: skip
    assert not any(t in json.dumps(listed, default=str) for t in tokens.values())

    summary = label_summary(configured, "fixture-set")
    assert summary["gold_test_labels"] == {"AGRICULTURAL_BURN": 1}
    assert summary["double_reviewed_cases"] == 1 and summary["pending_adjudication"] == 0
    assert summary["kappa_pairs"] == 1  # "cannot decide" pairs would be left out

    with database_engine(configured) as engine, engine.connect() as conn:
        stored = conn.execute(
            text("""SELECT l.role,l.blind,l.evidence,l.reviewer,a.name AS account
                FROM label_reviews l JOIN reviewers a ON a.id=l.reviewer_id
                ORDER BY l.reviewed_at""")
        ).all()
        hashes = set(conn.execute(text("SELECT token_sha256 FROM reviewers")).scalars())
        dump = json.dumps([list(r) for r in conn.execute(text("SELECT * FROM reviewers"))],
                          default=str)  # fmt: skip
    assert [r.role for r in stored] == ["REVIEWER", "REVIEWER", "ADJUDICATOR"]
    assert [r.reviewer for r in stored] == [r.account for r in stored] == ["Asha", "Ben", "Chen"]
    assert token_sha256(tokens["Asha"]) in hashes
    assert not any(t in dump for t in tokens.values())  # only hashes are stored
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
    for statement, message in (
        ("DELETE FROM reviewers", "never deleted"),
        ("TRUNCATE reviewers CASCADE", "never deleted"),
        ("UPDATE reviewers SET name='Mallory' WHERE name='Asha'", "immutable"),
    ):
        with pytest.raises(DBAPIError, match=message):
            with database_engine(configured) as engine, engine.begin() as conn:
                conn.execute(text(statement))
    insert = """INSERT INTO label_reviews (id,case_set_id,case_id,reviewer,reviewer_id,role,
        source_label,certainty,evidence,blind,reviewed_at)
        SELECT gen_random_uuid(),case_set_id,case_id,:name,{account},'ADJUDICATOR',
            'OTHER','LOW','{{}}'::jsonb,true,now() FROM label_reviews WHERE reviewer='Asha'"""
    for name, account, constraint in (
        ("ASHA", "reviewer_id", "ux_label_reviews"),  # one review per person, any letter case
        ("Zed", "NULL", "label_reviews_signed_in"),  # every new review names an account
    ):
        with pytest.raises(IntegrityError, match=constraint):
            with database_engine(configured) as engine, engine.begin() as conn:
                conn.execute(text(insert.format(account=account)), {"name": name})
    assert (
        case_set_fingerprint(configured, "fixture-set")["splits_sha256"] == (after["splits_sha256"])
    )

    # A misused token: its reviews stay stored but stop counting, the adjudication it provoked no
    # longer settles anything, the case returns to the queue, and the account stays closed.
    assert void_reviews(configured, "Ben")["reviews_voided"] == 1
    voided = label_summary(configured, "fixture-set")
    assert voided["gold_test_labels"] == {} and voided["reviews_voided"] == 1
    assert voided["reviews_total"] == 2 and voided["double_reviewed_cases"] == 0
    dev = client.get(f"{base}/queue", headers=auth("Dev")).json()
    reopened = next(i for i in dev["review"] if i["case_id"] == case_id)
    assert reopened["reviews"] == 1 and reopened["needs"] == 2
    with pytest.raises(ValueError, match="stays closed"):
        reactivate(configured, "Ben")
    with pytest.raises(LookupError):
        void_reviews(configured, "Ben")
    with pytest.raises(DBAPIError, match="stay voided"):
        with database_engine(configured) as engine, engine.begin() as conn:
            conn.execute(text("UPDATE reviewers SET reviews_voided_at=NULL WHERE name='Ben'"))

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
    # Downgrading would drop who wrote each review, so it is refused once accounts exist.
    with pytest.raises(DBAPIError, match="reviewer accounts exist"):
        command.downgrade(Config("alembic.ini"), "0007_review_integrity")


def test_reviewer_cli_saves_tokens_privately_and_never_prints_them(configured, tmp_path, capsys):
    from thermoscope.ml_cli import main
    from thermoscope.reviewers import authenticate

    first = tmp_path / "asha.token"
    assert (
        main(["add-reviewer", "--name", "Asha", "--adjudicator", "--token-file", str(first)]) == 0
    )
    out = capsys.readouterr().out
    token = first.read_text().strip()
    assert token not in out and json.loads(out)["can_adjudicate"] is True
    assert first.stat().st_mode & 0o777 == 0o600
    # An existing file is refused before the account changes, so no working token is lost.
    assert main(["rotate-reviewer-token", "--name", "Asha", "--token-file", str(first)]) == 1
    assert "TOKEN_FILE_EXISTS" in capsys.readouterr().out
    assert authenticate(configured, token)["name"] == "Asha"
    # A refused account change removes the file it had written.
    duplicate = tmp_path / "duplicate.token"
    assert main(["add-reviewer", "--name", "asha", "--token-file", str(duplicate)]) == 1
    assert "already exists" in capsys.readouterr().out and not duplicate.exists()
    rotated = tmp_path / "rotated.token"
    assert main(["rotate-reviewer-token", "--name", "Asha", "--token-file", str(rotated)]) == 0
    assert authenticate(configured, token) is None
    assert authenticate(configured, rotated.read_text().strip())["can_adjudicate"] is True
    assert main(["list-reviewers"]) == 0
    listing = capsys.readouterr().out
    assert token not in listing and rotated.read_text().strip() not in listing
    assert main(["void-reviewer", "--name", "Asha"]) == 0
    assert json.loads(capsys.readouterr().out)["reviews_voided"] == 0
    assert authenticate(configured, rotated.read_text().strip()) is None
