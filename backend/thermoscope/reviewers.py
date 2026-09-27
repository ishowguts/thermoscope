"""Per-person reviewer accounts (reviewer-accounts-v1, ADR-023).

Each reviewer holds a personal random token issued by the server owner. The server stores only
the token's SHA-256, looks the reviewer up from the token on every request and records the
account with each review, so a reviewer can no longer type someone else's name. This is sign-in
for a small team pilot, not single sign-on: there are no passwords, expiry or second factor, and
tokens must travel privately (and over HTTPS off this computer). Owners rotate or deactivate a
token when it may have leaked; accounts are never deleted.
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


def _issue() -> tuple[str, str]:
    token = TOKEN_PREFIX + secrets.token_urlsafe(32)  # 256 random bits
    return token, token_sha256(token)


def _clean_name(name: str) -> str:
    name = " ".join(str(name).split())
    if not NAME.fullmatch(name):
        raise ValueError("a reviewer name needs 2–60 letters, digits, spaces, . ' or -")
    return name


def add_reviewer(settings: Settings, name: str, can_adjudicate: bool = False):
    """Create an account; returns (account, token). The token is shown once and never stored."""
    name = _clean_name(name)
    token, digest = _issue()
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


def _update(settings: Settings, name: str, sql: str, params: dict) -> None:
    with database_engine(settings) as engine, engine.begin() as conn:
        done = conn.execute(
            text(f"UPDATE reviewers SET {sql} WHERE lower(name)=lower(:name)"),
            params | {"name": _clean_name(name)},
        ).rowcount
    if not done:
        raise LookupError("no reviewer with that name")


def rotate_token(settings: Settings, name: str) -> str:
    """Issue a new token (the old one stops working) and reactivate the account."""
    token, digest = _issue()
    _update(settings, name, "token_sha256=:h,token_issued_at=:now,active=true,deactivated_at=NULL",
            {"h": digest, "now": datetime.now(UTC)})  # fmt: skip
    return token


def deactivate(settings: Settings, name: str) -> None:
    _update(settings, name, "active=false,deactivated_at=:now", {"now": datetime.now(UTC)})


def list_reviewers(settings: Settings) -> list[dict]:
    with database_engine(settings) as engine, engine.connect() as conn:
        rows = conn.execute(
            text("""SELECT r.name,r.can_adjudicate,r.active,r.created_at,r.token_issued_at,
                    r.deactivated_at,count(l.id) AS reviews
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
