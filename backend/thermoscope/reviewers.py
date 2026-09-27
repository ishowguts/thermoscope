"""Per-person reviewer accounts (reviewer-accounts-v1, ADR-023).

Each reviewer holds a personal random token issued by the server owner. The server stores only
the token's SHA-256, looks the reviewer up from the token on every request and records the
account with each review, so a reviewer can no longer type someone else's name. This is sign-in
for a small team pilot, not single sign-on: there are no passwords, expiry or second factor, and
tokens must travel privately (and over HTTPS off this computer). Owners rotate or deactivate a
token when it may have leaked, and void an account's reviews if the token was misused; accounts are
never deleted.
"""

import hashlib
import os
import re
import secrets
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from thermoscope.config import Settings
from thermoscope.database import database_engine

SIGN_IN = "reviewer-accounts-v1"
TOKEN_PREFIX = "tsr_"
NAME = re.compile(r"[\w .'-]{2,60}")
TOKEN = re.compile(r"tsr_[A-Za-z0-9_-]{43}")


def token_sha256(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_token() -> str:
    return TOKEN_PREFIX + secrets.token_urlsafe(32)  # 256 random bits


def _issue(token: str | None = None) -> tuple[str, str]:
    token = token or new_token()
    if not TOKEN.fullmatch(token):
        raise ValueError("not a reviewer token")
    return token, token_sha256(token)


def _clean_name(name: str) -> str:
    name = " ".join(str(name).split())
    if not NAME.fullmatch(name):
        raise ValueError("a reviewer name needs 2–60 letters, digits, spaces, . ' or -")
    return name


def add_reviewer(settings: Settings, name: str, can_adjudicate: bool = False, token=None):
    """Create an account; returns (account, token). Only the token's hash is stored. The CLI
    passes a token it has already saved to the owner's file, so a failed save loses nothing."""
    name = _clean_name(name)
    token, digest = _issue(token)
    now = datetime.now(UTC)
    account = {"id": uuid4(), "name": name, "can_adjudicate": bool(can_adjudicate)}
    try:
        with database_engine(settings) as engine, engine.begin() as conn:
            conn.execute(
                text("""INSERT INTO reviewers (id,name,token_sha256,can_adjudicate,active,
                    created_at,token_issued_at) VALUES (:id,:name,:h,:adj,true,:now,:now)"""),
                account | {"h": digest, "adj": account["can_adjudicate"], "now": now},
            )
    except IntegrityError:
        raise ValueError("a reviewer with that name already exists") from None
    return account | {"id": str(account["id"])}, token


def _update(settings: Settings, name: str, sql: str, where: str, params: dict, missing: str) -> int:
    try:
        with database_engine(settings) as engine, engine.begin() as conn:
            done = conn.execute(
                text(f"UPDATE reviewers SET {sql} WHERE lower(name)=lower(:name) AND {where}"),
                params | {"name": _clean_name(name), "now": datetime.now(UTC)},
            ).rowcount
    except IntegrityError:
        raise ValueError("a voided account stays closed; add a new account") from None
    if not done:
        raise LookupError(missing)
    return done


def rotate_token(settings: Settings, name: str, token=None) -> str:
    """Replace an active account's token; the old one stops working at once."""
    token, digest = _issue(token)
    _update(settings, name, "token_sha256=:h,token_issued_at=:now", "active", {"h": digest},
            "no active reviewer with that name")  # fmt: skip
    return token


def reactivate(settings: Settings, name: str, token=None) -> str:
    """Reopen a deactivated account with a new token (the old token never works again)."""
    token, digest = _issue(token)
    _update(settings, name, "token_sha256=:h,token_issued_at=:now,active=true,deactivated_at=NULL",
            "NOT active", {"h": digest}, "no deactivated reviewer with that name")  # fmt: skip
    return token


def deactivate(settings: Settings, name: str) -> None:
    _update(settings, name, "active=false,deactivated_at=:now", "active", {},
            "no active reviewer with that name")  # fmt: skip


def void_reviews(settings: Settings, name: str) -> dict:
    """For a misused token: close the account and stop all its reviews from counting (they stay
    stored for audit). Affected cases return to the queue. Cannot be undone."""
    _update(
        settings,
        name,
        "active=false,deactivated_at=COALESCE(deactivated_at,:now),reviews_voided_at=:now",
        "reviews_voided_at IS NULL",
        {},
        "no reviewer with that name, or already voided",
    )
    with database_engine(settings) as engine, engine.connect() as conn:
        count = conn.execute(
            text("""SELECT count(*) FROM label_reviews l JOIN reviewers r ON r.id=l.reviewer_id
                WHERE lower(r.name)=lower(:name)"""),
            {"name": _clean_name(name)},
        ).scalar_one()
    return {"name": _clean_name(name), "active": False, "reviews_voided": count}


def list_reviewers(settings: Settings) -> list[dict]:
    with database_engine(settings) as engine, engine.connect() as conn:
        rows = conn.execute(
            text("""SELECT r.name,r.can_adjudicate,r.active,r.created_at,r.token_issued_at,
                    r.deactivated_at,r.reviews_voided_at,count(l.id) AS reviews
                FROM reviewers r LEFT JOIN label_reviews l ON l.reviewer_id=r.id
                GROUP BY r.id ORDER BY lower(r.name)""")
        ).mappings()
        return [dict(r) for r in rows]


def reviewers_configured(settings: Settings) -> bool:
    with database_engine(settings) as engine, engine.connect() as conn:
        return bool(conn.execute(text("SELECT EXISTS (SELECT 1 FROM reviewers WHERE active)"))
                    .scalar())  # fmt: skip


def bearer_token(header: str | None) -> str | None:
    """`Authorization: Bearer tsr_…`; anything else is treated as no token."""
    if not header:
        return None
    scheme, _, value = header.strip().partition(" ")
    value = value.strip()
    if scheme.lower() != "bearer" or not TOKEN.fullmatch(value):
        return None
    return value


def authenticate(settings: Settings, token: str | None) -> dict | None:
    """The active account holding this token, or None. Lookup is by hash of a 256-bit token."""
    if token is None:
        return None
    with database_engine(settings) as engine, engine.connect() as conn:
        row = (
            conn.execute(
                text("""SELECT id,name,can_adjudicate FROM reviewers
                    WHERE token_sha256=:h AND active"""),
                {"h": token_sha256(token)},
            )
            .mappings()
            .first()
        )
    return None if row is None else {"id": str(row["id"]), "name": row["name"],
                                     "can_adjudicate": row["can_adjudicate"]}  # fmt: skip


def write_token_file(path: Path, token: str) -> Path:
    """Save a new token for the owner to pass on privately: owner-only permissions, no overwrite,
    so the token never has to appear in a terminal, log or chat."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as handle:
        handle.write(token + "\n")
    return path
