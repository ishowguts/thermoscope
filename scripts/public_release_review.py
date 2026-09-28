"""Public-release review of the tracked files (P08-REL-001). Nothing is published or changed.

    python3 scripts/public_release_review.py --terms local/public-review-terms.txt \\
        --out docs/inventory/public-release-review.csv

Lists every file Git tracks with its category, what in it needs a decision before any public
copy (team or personal identity, a local user path, internal process records, a possible
credential) and a suggested decision. Identity terms (team name, team ID, names, institute,
account handles) are read from an ignored local file, one per line, so this script and its report
never repeat them. The repository has no code licence yet, so every file also needs that
decision. Prints a JSON summary; exits 1 if anything that looks like a credential is found.
"""

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

CREDENTIAL = re.compile(
    rb"BEGIN [A-Z ]*PRIVATE KEY|tsr_[A-Za-z0-9_-]{43}|ghp_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}"
    rb"|firms\.modaps\.eosdis\.nasa\.gov/api/[a-z]+/csv/[A-Za-z0-9]{32}"
    # a database URL with an inline password, except f-string placeholders and known fixtures
    rb"|postgres(?:ql)?(?:\+psycopg)?://[^:\s/]+:"
    rb"(?!\{|disposable-ci-only@|private-test-password@|p@|x@)[^@\s]{6,}@"
)
LOCAL_PATH = re.compile(rb"/Users/[A-Za-z0-9._-]+|C:\\\\Users\\\\")
PROCESS = ("docs/tasks/", "docs/review/")


def category(path: str) -> str:
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
    if path.endswith((".md",)):
        return "documentation"
    if path.endswith((".lock", "package-lock.json")):
        return "lockfile"
    return "configuration"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--terms", type=Path, required=True, help="identity terms, one per line")
    parser.add_argument(
        "--out", type=Path, default=Path("docs/inventory/public-release-review.csv")
    )
    args = parser.parse_args(argv)
    terms = [t.strip().encode() for t in args.terms.read_text().splitlines() if t.strip()]
    files = subprocess.run(["git", "ls-files"], capture_output=True, text=True,
                           check=True).stdout.split()  # fmt: skip
    rows, credentials = [], []
    for path in files:
        data = Path(path).read_bytes() if Path(path).is_file() else b""
        flags = []
        if any(re.search(re.escape(t), data, re.IGNORECASE) for t in terms):
            flags.append("team or personal identity")
        if LOCAL_PATH.search(data):
            flags.append("local user path")
        if CREDENTIAL.search(data):
            flags.append("possible credential")
            credentials.append(path)
        kind = category(path)
        if kind == "process record":
            flags.append("internal process record")
        decision = "decide: " + "; ".join(flags) if flags else "keep once a code licence is chosen"
        rows.append({"path": path, "bytes": len(data), "category": kind,
                     "needs_decision": "; ".join(flags), "suggested": decision})  # fmt: skip
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    counts: dict[str, int] = {}
    for row in rows:
        for flag in filter(None, row["needs_decision"].split("; ")):
            counts[flag] = counts.get(flag, 0) + 1
    print(json.dumps({"tracked_files": len(rows), "flags": counts,
                      "largest_bytes": max(r["bytes"] for r in rows),
                      "possible_credentials": credentials, "report": str(args.out)}))  # fmt: skip
    return 1 if credentials else 0


if __name__ == "__main__":
    sys.exit(main())
