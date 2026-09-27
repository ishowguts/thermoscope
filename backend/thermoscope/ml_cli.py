"""P05 CLI: registry evidence, frozen case sets, features, training/evaluation and summaries."""

import argparse
import json
from datetime import datetime
from pathlib import Path

from thermoscope.config import DataMode, Settings
from thermoscope.firms import IngestError


def main(argv=None):
    parser = argparse.ArgumentParser(description="ThermoScope P05 labels and models")
    parser.add_argument(
        "command",
        choices=["import-gppd", "build-cases", "landcover", "features", "train", "summary"],
    )
    parser.add_argument("--case-set", help="case-set name or id")
    parser.add_argument("--name", help="new case-set name (lowercase, digits, - or _)")
    parser.add_argument("--data-mode", choices=list(DataMode), default=DataMode.HISTORICAL_REPLAY)
    parser.add_argument("--file", type=Path)
    parser.add_argument("--sha256")
    parser.add_argument("--retrieved-at", type=datetime.fromisoformat)
    parser.add_argument(
        "--dry-run-weak",
        action="store_true",
        help="exercise the pipeline with rule-derived labels; never evidence of performance",
    )
    args = parser.parse_args(argv)
    settings = Settings()
    try:
        if args.command == "import-gppd":
            if not (args.file and args.sha256 and args.retrieved_at):
                parser.error("import-gppd needs --file, --sha256 and --retrieved-at")
            from thermoscope.labels import import_gppd

            report = import_gppd(settings, args.file.read_bytes(), args.sha256, args.retrieved_at)
        elif args.command == "build-cases":
            if not args.name:
                parser.error("build-cases needs --name")
            from thermoscope.labels import build_case_set

            report = build_case_set(settings, args.name, DataMode(args.data_mode))
        elif args.command == "landcover":
            from thermoscope.ml import extract_case_landcover

            report = extract_case_landcover(settings, _need(parser, args.case_set))
        elif args.command == "features":
            from thermoscope.ml import compute_case_features

            report = compute_case_features(settings, _need(parser, args.case_set))
        elif args.command == "train":
            from thermoscope.ml import train_and_evaluate

            report = train_and_evaluate(
                settings, _need(parser, args.case_set), dry_run_weak=args.dry_run_weak
            )
        else:
            from thermoscope.labels import label_summary

            report = label_summary(settings, _need(parser, args.case_set))
        print(json.dumps(report, indent=2, default=str))
        return 0
    except (IngestError, ValueError, LookupError) as error:
        code = error.code if isinstance(error, IngestError) else "INVALID_REQUEST"
        print(json.dumps({"status": "FAILED", "error_code": code, "detail": str(error)[:200]}))
        return 1


def _need(parser, value):
    if not value:
        parser.error("this command needs --case-set")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
