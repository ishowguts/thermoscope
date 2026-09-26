"""CLI entry point. Values from secrets and driver exceptions are never printed."""

import argparse
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from thermoscope.config import DataMode, Settings
from thermoscope.firms import MAX_BYTES, IngestError
from thermoscope.ingestion import ingest
from thermoscope.regions import REGIONS, Bounds, Product, Window


def main():
    parser = argparse.ArgumentParser(description="Bounded NASA FIRMS observation ingestion")
    parser.add_argument("command", choices=["fetch", "import-file"])
    parser.add_argument("--region", choices=[r["id"] for r in REGIONS], default="jamnagar")
    parser.add_argument("--product", choices=list(Product), default=Product.NOAA20)
    parser.add_argument("--start-date", type=date.fromisoformat)
    parser.add_argument("--days", type=int, default=5)
    parser.add_argument("--file", type=Path)
    parser.add_argument("--sha256")
    args = parser.parse_args()
    if args.command == "import-file" and (not args.file or not args.start_date or not args.sha256):
        parser.error("import-file requires --file, --sha256 and --start-date")
    if args.command == "fetch" and (args.file or args.sha256):
        parser.error("fetch does not accept file settings")
    try:
        bounds = Bounds.parse(next(r["bbox"] for r in REGIONS if r["id"] == args.region))
        window = Window(
            product=args.product,
            bounds=bounds,
            days=args.days,
            start_date=args.start_date or datetime.now(UTC).date() - timedelta(days=args.days - 1),
        )
        payload = None
        if args.file:
            with args.file.open("rb") as stream:
                payload = stream.read(MAX_BYTES + 1)
        mode = DataMode.LIVE if args.command == "fetch" else DataMode.HISTORICAL_REPLAY
        report = ingest(Settings(), window, mode, payload=payload, expected_sha256=args.sha256)
        print(json.dumps(report))
        return 1 if report["status"] == "FAILED" else 0
    except Exception as error:
        code = error.code if isinstance(error, IngestError) else "CONFIGURATION_OR_DEPENDENCY_ERROR"
        print(json.dumps({"status": "FAILED", "error_code": code}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
