"""P05 CLI: registry evidence, frozen case sets, features, training/evaluation, summaries and
reviewer accounts. New reviewer tokens are written to an owner-only file, never printed."""

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from thermoscope.config import DataMode, Settings
from thermoscope.firms import IngestError


def main(argv=None):
    parser = argparse.ArgumentParser(description="ThermoScope P05 labels and models")
    parser.add_argument(
        "command",
        choices=[
            "import-gppd",
            "build-cases",
            "landcover",
            "features",
            "train",
            "summary",
            "grouping-audit",
            "fingerprint",
            "add-reviewer",
            "rotate-reviewer-token",
            "reactivate-reviewer",
            "deactivate-reviewer",
            "void-reviewer",
            "list-reviewers",
        ],
    )
    parser.add_argument(
        "--grouping", default="facility-aware-v1", help="site-2km-v1 or facility-aware-v1 (default)"
    )
    parser.add_argument("--supersedes", help="case set this new set replaces (needs --reason)")
    parser.add_argument("--reason", help="recorded reason for superseding")  # fmt: skip
    parser.add_argument("--case-set", help="case-set name or id")
    parser.add_argument("--name", help="new case-set name, or a reviewer's name")
    parser.add_argument("--adjudicator", action="store_true", help="reviewer may adjudicate")
    parser.add_argument(
        "--token-file",
        type=Path,
        help="file for a new reviewer token (default local/reviewer-tokens/<name>-<time>.token)",
    )
    parser.add_argument("--data-mode", choices=list(DataMode), default=DataMode.HISTORICAL_REPLAY)
    parser.add_argument("--file", type=Path)
    parser.add_argument("--sha256")
    parser.add_argument("--retrieved-at", type=datetime.fromisoformat)
    parser.add_argument(
        "--allow-partial-history",
        action="store_true",
        help="features: write rows even though the saved archive misses part of the history "
        "window (those cases are set aside by history-eligibility-v1)",
    )
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

            report = build_case_set(
                settings,
                args.name,
                DataMode(args.data_mode),
                grouping=args.grouping,
                supersedes=args.supersedes,
                reason=args.reason,
            )
        elif args.command == "landcover":
            from thermoscope.ml import extract_case_landcover

            report = extract_case_landcover(settings, _need(parser, args.case_set))
        elif args.command == "features":
            from thermoscope.ml import compute_case_features

            report = compute_case_features(
                settings,
                _need(parser, args.case_set),
                allow_partial_history=args.allow_partial_history,
            )
        elif args.command == "train":
            from thermoscope.ml import train_and_evaluate

            report = train_and_evaluate(
                settings, _need(parser, args.case_set), dry_run_weak=args.dry_run_weak
            )
        elif args.command == "grouping-audit":
            from thermoscope.labels import grouping_audit

            report = grouping_audit(settings, _need(parser, args.case_set))
        elif args.command in {"add-reviewer", "rotate-reviewer-token", "reactivate-reviewer"}:
            from thermoscope import reviewers

            if not args.name:
                parser.error(f"{args.command} needs --name")
            # The token is saved to the owner-only file first; the account changes only after
            # that succeeded, and the file is removed again if the account change fails.
            token = reviewers.new_token()
            try:
                path = reviewers.write_token_file(args.token_file or _token_path(args.name), token)
            except FileExistsError:
                raise IngestError("TOKEN_FILE_EXISTS") from None
            except OSError:
                raise IngestError("TOKEN_FILE_NOT_WRITTEN") from None
            try:
                if args.command == "add-reviewer":
                    account, _ = reviewers.add_reviewer(
                        settings, args.name, args.adjudicator, token=token
                    )
                elif args.command == "rotate-reviewer-token":
                    reviewers.rotate_token(settings, args.name, token=token)
                    account = {"name": args.name, "token": "replaced; the old one no longer works"}
                else:
                    reviewers.reactivate(settings, args.name, token=token)
                    account = {"name": args.name, "active": True, "token": "new"}
            except BaseException:
                path.unlink(missing_ok=True)
                raise
            report = account | {
                "token_file": str(path),
                "next": "Give this token to the reviewer privately, then delete the file. It is "
                "not stored on the server and cannot be shown again (rotate to reissue).",
            }
        elif args.command in {"deactivate-reviewer", "void-reviewer"}:
            from thermoscope import reviewers

            if not args.name:
                parser.error(f"{args.command} needs --name")
            if args.command == "deactivate-reviewer":
                reviewers.deactivate(settings, args.name)
                report = {"name": args.name, "active": False}
            else:
                report = reviewers.void_reviews(settings, args.name)
        elif args.command == "list-reviewers":
            from thermoscope.reviewers import list_reviewers

            report = {"reviewers": list_reviewers(settings)}
        elif args.command == "fingerprint":
            from thermoscope.labels import case_set_fingerprint

            report = case_set_fingerprint(settings, _need(parser, args.case_set))
        else:
            from thermoscope.labels import label_summary

            report = label_summary(settings, _need(parser, args.case_set))
        print(json.dumps(report, indent=2, default=str))
        return 0
    except (IngestError, ValueError, LookupError) as error:
        code = error.code if isinstance(error, IngestError) else "INVALID_REQUEST"
        print(json.dumps({"status": "FAILED", "error_code": code, "detail": str(error)[:200]}))
        return 1


def _token_path(name: str) -> Path:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "reviewer"
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    return Path("local/reviewer-tokens") / f"{slug}-{stamp}.token"


def _need(parser, value):
    if not value:
        parser.error("this command needs --case-set")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
