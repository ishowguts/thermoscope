"""Release dependency audit (P08-REL-001): known vulnerabilities and licences of the locked
Python and npm packages.

    PYTHONPATH=backend bash scripts/run.sh uv run --frozen python scripts/release_audit.py \\
        --out local/release-audit.json

Vulnerabilities come from the public OSV database (https://osv.dev) for the exact versions in
`uv.lock` and `frontend/package-lock.json` (all groups, including the optional ML group and
development tools). Python licences are read from the installed distributions' metadata, so
run it after `make install && make install-ml`; npm licences come from the lockfile. This is a
dependency snapshot, not legal clearance or a full security review. Prints a one-line JSON
summary; exits 1 when a vulnerability is reported or a licence needs a decision.
"""

import argparse
import json
import sys
import tomllib
import urllib.request
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path

OSV_BATCH = "https://api.osv.dev/v1/querybatch"
PERMISSIVE = {
    "MIT", "MIT-0", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "ISC", "PSF-2.0", "0BSD",
    "Python-2.0", "Unlicense", "CC0-1.0", "BlueOak-1.0.0", "Zlib", "HPND",
}  # fmt: skip
WEAK_COPYLEFT = {"MPL-2.0", "LGPL-2.1-or-later", "LGPL-3.0-or-later", "EPL-2.0"}
CLASSIFIER = {
    "MIT License": "MIT", "BSD License": "BSD-3-Clause", "Apache Software License": "Apache-2.0",
    "ISC License (ISCL)": "ISC", "Python Software Foundation License": "PSF-2.0",
    "Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
}  # fmt: skip


def python_packages(lock_path: Path) -> list[dict]:
    lock = tomllib.loads(lock_path.read_text())
    packages = []
    for package in lock["package"]:
        source = package.get("source", {})
        if "virtual" in source or "editable" in source:
            continue  # the project itself
        packages.append({"ecosystem": "PyPI", "name": package["name"],
                         "version": package["version"]})  # fmt: skip
    return packages


def npm_packages(lock_path: Path) -> list[dict]:
    lock = json.loads(lock_path.read_text())
    packages = []
    for path, info in lock["packages"].items():
        if not path:
            continue  # the application itself
        name = info.get("name") or path.split("node_modules/")[-1]
        packages.append({
            "ecosystem": "npm", "name": name, "version": info["version"],
            "license": info.get("license"),
            "scope": "development" if info.get("dev") else "runtime",
        })  # fmt: skip
    return packages


def osv(packages: list[dict]) -> list[list[str]]:
    results: list[list[str]] = []
    for start in range(0, len(packages), 500):
        chunk = packages[start : start + 500]
        body = json.dumps({"queries": [
            {"package": {"name": p["name"], "ecosystem": p["ecosystem"]}, "version": p["version"]}
            for p in chunk
        ]}).encode()  # fmt: skip
        request = urllib.request.Request(OSV_BATCH, data=body,
                                         headers={"Content-Type": "application/json"})  # fmt: skip
        with urllib.request.urlopen(request, timeout=60) as response:
            answer = json.load(response)
        results += [[v["id"] for v in r.get("vulns", [])] for r in answer["results"]]
    return results


def python_licence(name: str) -> str | None:
    try:
        meta = metadata.metadata(name)
    except metadata.PackageNotFoundError:
        return None
    if meta.get("License-Expression"):
        return meta["License-Expression"]
    for classifier in meta.get_all("Classifier") or []:
        if classifier.startswith("License :: OSI Approved :: "):
            label = classifier.rsplit(" :: ", 1)[-1]
            return CLASSIFIER.get(label, label)
    text = (meta.get("License") or "").strip()
    return text.splitlines()[0][:60] if text else None


def pypi_licence(name: str, version: str) -> str | None:
    """Licence of a locked package that is not installed here (another platform or group)."""
    url = f"https://pypi.org/pypi/{name}/{version}/json"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            info = json.load(response)["info"]
    except (OSError, ValueError, KeyError):
        return None
    if info.get("license_expression"):
        return info["license_expression"]
    for classifier in info.get("classifiers") or []:
        if classifier.startswith("License :: OSI Approved :: "):
            label = classifier.rsplit(" :: ", 1)[-1]
            return CLASSIFIER.get(label, label)
    text = (info.get("license") or "").strip()
    return text.splitlines()[0][:60] if text else None


def classify(expression: str | None) -> str:
    if not expression:
        return "UNKNOWN"
    options = [part.strip(" ()") for part in expression.replace(" or ", " OR ").split(" OR ")]
    if any(option in PERMISSIVE for option in options):
        return "PERMISSIVE"
    parts = [p.strip(" ()") for p in expression.replace(" AND ", " OR ").split(" OR ")]
    if all(p in PERMISSIVE for p in parts):
        return "PERMISSIVE"
    if any(p in WEAK_COPYLEFT for p in parts):
        return "WEAK_COPYLEFT"
    if any(p.startswith(("GPL", "AGPL", "LGPL")) for p in parts):
        return "COPYLEFT"
    return "REVIEW"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="local/release-audit.json")
    args = parser.parse_args(argv)
    python = python_packages(Path("uv.lock"))
    npm = npm_packages(Path("frontend/package-lock.json"))
    for package in python:
        try:
            metadata.distribution(package["name"])
            package["scope"] = "installed"
            package["license"] = python_licence(package["name"])
        except metadata.PackageNotFoundError:
            package["scope"] = "not installed here"
            package["license"] = pypi_licence(package["name"], package["version"])
    everything = python + npm
    for package, ids in zip(everything, osv(everything), strict=True):
        package["vulnerabilities"] = ids
        package["license_class"] = classify(package["license"])
    vulnerable = [p for p in everything if p["vulnerabilities"]]
    decisions = [p for p in everything if p["license_class"] not in {"PERMISSIVE"}]
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "sources": {
            "vulnerabilities": OSV_BATCH,
            "python_licences": "installed metadata",
            "npm_licences": "frontend/package-lock.json",
        },  # fmt: skip
        "counts": {
            "python": len(python),
            "npm": len(npm),
            "npm_runtime": sum(p["scope"] == "runtime" for p in npm),
            "vulnerable": len(vulnerable),
            "licence_decisions": len(decisions),
        },  # fmt: skip
        "vulnerable": vulnerable,
        "licence_decisions": decisions,
        "packages": everything,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=1) + "\n")
    summary = report["counts"] | {
        "licence_decision_packages": sorted(
            f"{p['ecosystem']}:{p['name']}@{p['version']} {p['license']} ({p['scope']})"
            for p in decisions
        ),
        "report": args.out,
    }
    print(json.dumps(summary))
    return 1 if vulnerable or decisions else 0


if __name__ == "__main__":
    sys.exit(main())
