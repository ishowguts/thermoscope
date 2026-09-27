"""Context CLI. Driver exceptions and request details are never printed."""

import argparse
import json
from datetime import datetime
from pathlib import Path

from thermoscope.config import DataMode, Settings
from thermoscope.context_ingestion import ingest_osm
from thermoscope.events import build_event_run
from thermoscope.firms import IngestError
from thermoscope.landcover import extract_landcover
from thermoscope.osm import MAX_BYTES, OVERPASS_ENDPOINTS
from thermoscope.regions import REGIONS


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Bounded regional facility context and event/site grouping"
    )
    parser.add_argument(
        "command", choices=["fetch-osm", "import-osm", "build-events", "extract-landcover"]
    )
    parser.add_argument("--region", choices=[r["id"] for r in REGIONS], required=True)
    parser.add_argument("--file", type=Path)
    parser.add_argument("--sha256")
    parser.add_argument(
        "--retrieved-at",
        type=datetime.fromisoformat,
        help="Original UTC retrieval time of a saved response, with timezone",
    )
    parser.add_argument("--endpoint", choices=OVERPASS_ENDPOINTS)
    parser.add_argument("--data-mode", choices=list(DataMode), default=DataMode.HISTORICAL_REPLAY)
    parser.add_argument("--force", action="store_true", help="Recompute even if inputs match")
    args = parser.parse_args(argv)
    if args.command == "import-osm" and (not args.file or not args.sha256):
        parser.error("import-osm requires --file and --sha256")
    if args.command == "fetch-osm" and (args.file or args.sha256 or args.retrieved_at):
        parser.error("fetch-osm does not accept file settings")
    try:
        if args.command == "extract-landcover":
            report = extract_landcover(
                Settings(), args.region, DataMode(args.data_mode), force=args.force
            )
            print(json.dumps(report))
            return 1 if report["status"] == "PARTIAL" else 0
        if args.command == "build-events":
            report = build_event_run(
                Settings(), args.region, DataMode(args.data_mode), force=args.force
            )
            print(json.dumps(report))
            return 0
        payload = None
        if args.file:
            with args.file.open("rb") as stream:
                payload = stream.read(MAX_BYTES + 1)
        report = ingest_osm(
            Settings(),
            args.region,
            payload=payload,
            expected_sha256=args.sha256,
            retrieved_at=args.retrieved_at,
            endpoint=args.endpoint,
        )
        print(json.dumps(report))
        return 1 if report["status"] == "FAILED" else 0
    except Exception as error:
        code = error.code if isinstance(error, IngestError) else "CONFIGURATION_OR_DEPENDENCY_ERROR"
        print(json.dumps({"status": "FAILED", "error_code": code}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
