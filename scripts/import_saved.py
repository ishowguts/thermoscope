"""Import saved FIRMS CSVs and Overpass responses that have `.meta.json` sidecars.

Usage (from the repository root, after `make migrate`):

    PYTHONPATH=backend bash scripts/run.sh uv run --frozen python scripts/import_saved.py \
        --firms-dir local/p05-fetch/raw --osm-dir local/context-fetch

Every file's SHA-256 must match its sidecar. Files are imported as historical replay; re-running
is safe (identical rows and snapshots are reused). Prints one JSON summary; never prints keys.
"""

import argparse
import glob
import hashlib
import json
import os
from collections import Counter
from datetime import date, datetime

from thermoscope.config import DataMode, Settings
from thermoscope.context_ingestion import ingest_osm
from thermoscope.ingestion import ingest
from thermoscope.regions import REGIONS, Bounds, Product, Window


def sidecars(directory: str, pattern: str):
    for meta in sorted(glob.glob(os.path.join(directory, pattern))):
        path = meta[: -len(".meta.json")]
        with open(meta) as handle:
            info = json.load(handle)
        with open(path, "rb") as handle:
            payload = handle.read()
        if hashlib.sha256(payload).hexdigest() != info["content_sha256"]:
            raise SystemExit(f"hash mismatch: {path}")
        yield path, info, payload


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--firms-dir")
    parser.add_argument("--osm-dir")
    args = parser.parse_args()
    settings = Settings()
    boxes = {r["id"]: Bounds.parse(r["bbox"]) for r in REGIONS}
    report = {"firms": Counter(), "inserted": Counter(), "osm": {}, "problems": []}
    if args.firms_dir:
        for path, info, payload in sidecars(args.firms_dir, "*.csv.meta.json"):
            window = Window(
                product=Product(info["product"]),
                bounds=boxes[info["region"]],
                start_date=date.fromisoformat(info["start_date"]),
                days=info["days"],
            )
            result = ingest(settings, window, DataMode.HISTORICAL_REPLAY, payload=payload,
                            expected_sha256=info["content_sha256"])  # fmt: skip
            report["firms"][result["status"]] += 1
            report["inserted"][info["region"]] += result.get("inserted_rows", 0)
            if result["status"] != "SUCCEEDED":
                report["problems"].append({"file": os.path.basename(path), "result": result})
    if args.osm_dir:
        for path, info, payload in sidecars(args.osm_dir, "*-osm-*.json.meta.json"):
            result = ingest_osm(
                settings,
                info["region"],
                payload=payload,
                expected_sha256=info["content_sha256"],
                retrieved_at=datetime.fromisoformat(info["received_at"].replace("Z", "+00:00")),
                endpoint=info["endpoint"],
            )
            report["osm"][os.path.basename(path)] = {
                k: result.get(k) for k in ("status", "accepted_elements", "rejected_elements")
            }
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
