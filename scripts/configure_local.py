"""Prepare ignored local settings without replacing existing credentials."""

import os
import re
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / ".env"
content = path.read_text() if path.exists() else (root / ".env.example").read_text()


def read_value(name: str) -> str:
    match = re.search(rf"^{name}=(.*)$", content, re.MULTILINE)
    return match.group(1).strip() if match else ""


def set_value(name: str, value: str) -> None:
    global content
    pattern = rf"^{name}=.*$"
    if re.search(pattern, content, re.MULTILINE):
        content = re.sub(pattern, lambda _: f"{name}={value}", content, flags=re.MULTILINE)
    else:
        content = content.rstrip() + f"\n{name}={value}\n"


if not read_value("DATABASE_URL"):
    password = read_value("POSTGRES_PASSWORD") or secrets.token_hex(24)
    # Generated passwords are URL-safe; refuse an existing non-hex value instead of misquoting it.
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", password):
        raise SystemExit(
            "Existing POSTGRES_PASSWORD needs manual URL encoding; settings unchanged."
        )
    set_value("POSTGRES_PASSWORD", password)
    set_value(
        "DATABASE_URL",
        f"postgresql+psycopg://thermoscope:{password}@127.0.0.1:55432/thermoscope_dev",
    )

fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w") as stream:
    stream.write(content)
path.chmod(0o600)
print("Local settings prepared. Existing credentials preserved; no values displayed.")
