"""Public-release review of the committed files (P08-REL-001). Nothing is published or changed.

    python3 scripts/public_release_review.py --terms local/public-review-terms.txt \\
        --out docs/inventory/public-release-review.csv

Lists every file in the HEAD commit with its category, what in it needs a decision before any
public copy (team or personal identity, a local user path, internal process records, a
possible credential) and a suggested decision. Identity terms (team name, team ID, names,
institute, account handles) are read from an ignored local file, one per line, so this script and
its report never repeat them. The repository has no code licence yet, so every file also needs
that decision. The credential patterns are a screen, not proof of absence: also compare the real
local secrets against the exact allowlist before publishing. Prints a JSON summary (paths only,
never matched text); exits 1 if anything that looks like a credential is found.
"""

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

REPORT = "docs/inventory/public-release-review.csv"
# Placeholders and published fixtures that are not secrets.
NOT_SECRET = (
    rb"(?!\{|\$|<|disposable-ci-only\b|private-test-password\b|change-?me\b|Sentinel|p@|x@)"
)
CREDENTIAL = re.compile(
    rb"BEGIN [A-Z ]*PRIVATE KEY"
    rb"|tsr_[A-Za-z0-9_-]{43}"  # personal reviewer token
    rb"|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16}"
    rb"|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"  # JWT (e.g. Earthdata)
    rb"|firms\.modaps\.eosdis\.nasa\.gov/api/[a-z_]+/csv/[A-Za-z0-9]{32}"
    rb"|MAP_KEY[ \t]*[=:][ \t]*[\"']?[A-Za-z0-9]{32}"
    rb"|postgres(?:ql)?(?:\+psycopg)?://[^:\s/@]+:" + NOT_SECRET + rb"[^@\s]+@"
    # NAME=value on one line; names of storage keys, prefixes, files or headers are not secrets
    rb"|(?:PASSWORD|SECRET|TOKEN|API_KEY)(?![A-Z_]*_(?:KEY|NAME|PREFIX|FILE|PATH|HEADER)\b)"
    rb"[A-Z_]*[ \t]*[=:][ \t]*[\"']?" + NOT_SECRET + rb"[A-Za-z0-9_+/=.~-]{8,}(?=[\"'\s]|$)"
)
LOCAL_PATH = re.compile(rb"/Users/[A-Za-z0-9._-]+|/home/[a-z][a-z0-9_-]*/|C:\\\\Users\\\\")
PROCESS = ("docs/tasks/",
           "docs/review/")  # fmt: skip


def category(path: str) -> str:
    if path == REPORT:
        return "this release review"
    if path.startswith(PROCESS):
        return "process record"
    if path.startswith("docs/inventory/"):
        return "data inventory (hashes and dates of public source files)"
    if path.startswith("backend/tests/"):
        return "tests"
    if path.startswith(("backend/", "scripts/")):
        return "backend source"
    if path.startswith("frontend/"):
        return "frontend source/config"
    if path.endswith(".md"):
        return "documentation"
    if path.endswith((".lock", "package-lock.json")):
        return "lockfile"
    return "configuration"


def review(path: str, data: bytes, terms: list[bytes]) -> list[str]:
    flags = []
    if any(re.search(re.escape(t), data, re.IGNORECASE) for t in terms):
        flags.append("team or personal identity")
    if LOCAL_PATH.search(data):
        flags.append("local user path")
    if CREDENTIAL.search(data):
        flags.append("possible credential")
    if category(path) == "process record":
        flags.append("internal process record")
    return flags


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--terms", type=Path, required=True, help="identity terms, one per line")
    parser.add_argument("--out", type=Path, default=Path(REPORT))
    args = parser.parse_args(argv)
    terms = [t.strip().encode() for t in args.terms.read_text().splitlines() if t.strip()]
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                            text=True, check=True).stdout.strip()  # fmt: skip
    listing = subprocess.run(["git", "ls-tree", "-r", "-z", "--name-only", "HEAD"],
                             capture_output=True, check=True).stdout  # fmt: skip
    rows, credentials = [], []
    for path in filter(None, listing.decode().split("\0")):
        data = subprocess.run(["git", "show", f"HEAD:{path}"], capture_output=True,
                              check=True).stdout  # fmt: skip
        flags = review(path, data, terms)
        if "possible credential" in flags:
            credentials.append(path)
        rows.append({
            "path": path, "commit": commit, "bytes": len(data), "category": category(path),
            "needs_decision": "; ".join(flags),
            "suggested": "decide: " + "; ".join(flags) if flags
            else "keep once a code licence is chosen",
        })  # fmt: skip
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    counts: dict[str, int] = {}
    for row in rows:
        for flag in filter(None, row["needs_decision"].split("; ")):
            counts[flag] = counts.get(flag, 0) + 1
    print(json.dumps({"commit": commit, "files": len(rows), "flags": counts,
                      "largest_bytes": max(r["bytes"] for r in rows),
                      "possible_credentials": credentials, "report": str(args.out)}))  # fmt: skip
    return 1 if credentials else 0


if __name__ == "__main__":
    sys.exit(main())
