"""Release dependency audit (P08-REL-001): known vulnerabilities and licences of the locked
Python and npm packages.

    PYTHONPATH=backend bash scripts/run.sh uv run --frozen python scripts/release_audit.py \\
        --out local/release-audit.json

Vulnerabilities come from the public OSV database (https://osv.dev) for the exact versions in
`uv.lock` and `frontend/package-lock.json` (all groups, including the optional ML group and
development tools). Python licences come from the installed distributions' metadata (run after
`make install && make install-ml`) or, for packages locked for other platforms, from PyPI; npm
licences come from the lockfile. Only package names and versions are sent. This is a dependency
snapshot, not legal clearance or a full security review; bundled native libraries inside binary
wheels are not inspected.

Prints a one-line JSON summary. Exit codes (distinct from Python's 1 and argparse's 2): 0 no
known vulnerability and every non-permissive licence is in the reviewed list below; 10 a
vulnerability is reported; 11 a licence needs a new decision; 12 a vulnerability or licence source
could not be reached; 13 the installed environment differs from the lockfile.
"""

import argparse
import json
import re
import sys
import tomllib
import urllib.error
import urllib.request
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path

OSV_BATCH = "https://api.osv.dev/v1/querybatch"
PERMISSIVE = {
    "MIT", "MIT-0", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "ISC", "PSF-2.0", "0BSD",
    "Python-2.0", "Unlicense", "CC0-1.0", "BlueOak-1.0.0", "Zlib", "HPND",
}  # fmt: skip
WEAK_COPYLEFT = {
    "MPL-2.0", "EPL-2.0", "LGPL-2.1-only", "LGPL-2.1-or-later", "LGPL-3.0-only",
    "LGPL-3.0-or-later",
}  # fmt: skip
CLASSIFIER = {
    "MIT License": "MIT", "BSD License": "BSD-3-Clause", "Apache Software License": "Apache-2.0",
    "ISC License (ISCL)": "ISC", "Python Software Foundation License": "PSF-2.0",
    "Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
}  # fmt: skip
# Reviewed on 28 September 2026 (docs/RELEASE.md §6): used unmodified as libraries or build tools.
ACCEPTED = {
    ("PyPI", "certifi", "MPL-2.0"): "CA bundle used unmodified",
    ("PyPI", "psycopg", "LGPL-3.0-only"): "database driver used unmodified as a library",
    ("PyPI", "psycopg-binary", "LGPL-3.0-only"): "driver binary used unmodified as a library",
    ("npm", "lightningcss*", "MPL-2.0"): "build-time CSS tool, not in the shipped bundle",
}


EXIT = {"vulnerable": 10, "undecided_licence": 11, "source_unavailable": 12, "version_drift": 13}


class SourceUnavailable(RuntimeError):
    pass


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
        if not path or "version" not in info:
            continue  # the application itself, links and workspaces
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
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                answer = json.load(response)
        except (urllib.error.URLError, OSError, ValueError) as error:
            raise SourceUnavailable(f"OSV query failed: {type(error).__name__}") from None
        results += [[v["id"] for v in r.get("vulns", [])] for r in answer["results"]]
    return results


def licence_from(meta_licence_expression, classifiers, text) -> str | None:
    if meta_licence_expression:
        return meta_licence_expression
    for classifier in classifiers or []:
        if classifier.startswith("License :: OSI Approved :: "):
            label = classifier.rsplit(" :: ", 1)[-1]
            return CLASSIFIER.get(label, label)
    text = (text or "").strip()
    return text.splitlines()[0][:60] if text else None


def pypi_licence(name: str, version: str) -> str | None:
    """Licence of a locked package that is not installed here (another platform or group)."""
    url = f"https://pypi.org/pypi/{name}/{version}/json"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            info = json.load(response)["info"]
    except (urllib.error.URLError, OSError, ValueError, KeyError) as error:
        raise SourceUnavailable(f"PyPI metadata failed: {type(error).__name__}") from None
    return licence_from(info.get("license_expression"), info.get("classifiers"),
                        info.get("license"))  # fmt: skip


def classify(expression: str | None) -> str:
    """The most restrictive class an SPDX-like expression forces: AND terms must all be met,
    and an OR term is as permissive as its most permissive option."""
    if not expression:
        return "UNKNOWN"
    text = re.sub(r"\s+(and|AND)\s+", " AND ", expression)
    text = re.sub(r"\s+(or|OR)\s+", " OR ", text)
    rank = {"PERMISSIVE": 0, "WEAK_COPYLEFT": 1, "REVIEW": 2, "COPYLEFT": 3}

    def one(term: str) -> str:
        term = term.strip(" ()")
        if term in PERMISSIVE:
            return "PERMISSIVE"
        if term in WEAK_COPYLEFT:
            return "WEAK_COPYLEFT"
        if term.startswith(("GPL", "AGPL")):
            return "COPYLEFT"
        return "REVIEW"

    worst = "PERMISSIVE"
    for conjunct in text.split(" AND "):
        best = min((one(option) for option in conjunct.split(" OR ")), key=rank.get)
        worst = max(worst, best, key=rank.get)
    return worst


def accepted(package: dict) -> str | None:
    for (ecosystem, name, licence), reason in ACCEPTED.items():
        same_name = package["name"] == name or (
            name.endswith("*") and package["name"].startswith(name[:-1])
        )
        if package["ecosystem"] == ecosystem and same_name and package["license"] == licence:
            return reason
    return None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="local/release-audit.json")
    args = parser.parse_args(argv)
    python = python_packages(Path("uv.lock"))
    npm = npm_packages(Path("frontend/package-lock.json"))
    try:
        for package in python:
            try:
                distribution = metadata.distribution(package["name"])
            except metadata.PackageNotFoundError:
                package["scope"] = "not installed here"
                package["license"] = pypi_licence(package["name"], package["version"])
                continue
            meta = distribution.metadata
            package["scope"] = "installed"
            package["installed_version"] = distribution.version
            package["license"] = licence_from(
                meta.get("License-Expression"), meta.get_all("Classifier"), meta.get("License")
            )
        everything = python + npm
        vulnerabilities = osv(everything)
    except SourceUnavailable as error:
        print(json.dumps({"status": "SOURCE_UNAVAILABLE", "detail": str(error)}))
        return EXIT["source_unavailable"]
    for package, ids in zip(everything, vulnerabilities, strict=True):
        package["vulnerabilities"] = ids
        package["license_class"] = classify(package["license"])
        if package["license_class"] != "PERMISSIVE":
            package["accepted_because"] = accepted(package)
    vulnerable = [p for p in everything if p["vulnerabilities"]]
    reviewed = [p for p in everything if p.get("accepted_because")]
    undecided = [
        p for p in everything
        if p["license_class"] != "PERMISSIVE" and not p.get("accepted_because")
    ]  # fmt: skip
    drift = [p for p in python if p.get("installed_version") not in (None, p["version"])]
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "sources": {
            "vulnerabilities": OSV_BATCH,
            "python_licences": "installed metadata; PyPI JSON when not installed here",
            "npm_licences": "frontend/package-lock.json",
        },  # fmt: skip
        "counts": {
            "python": len(python),
            "npm": len(npm),
            "npm_runtime": sum(p["scope"] == "runtime" for p in npm),
            "vulnerable": len(vulnerable),
            "licences_accepted": len(reviewed),
            "licences_undecided": len(undecided),
            "version_drift": len(drift),
        },  # fmt: skip
        "vulnerable": vulnerable,
        "licences_undecided": undecided,
        "licences_accepted": reviewed,
        "version_drift": drift,
        "packages": everything,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=1) + "\n")

    def label(p):
        return f"{p['ecosystem']}:{p['name']}@{p['version']} {p['license']} ({p['scope']})"

    print(json.dumps(report["counts"] | {
        "vulnerable_packages": sorted(label(p) for p in vulnerable),
        "undecided_packages": sorted(label(p) for p in undecided),
        "report": args.out,
    }))  # fmt: skip
    if vulnerable:
        return EXIT["vulnerable"]
    if undecided:
        return EXIT["undecided_licence"]
    return EXIT["version_drift"] if drift else 0


if __name__ == "__main__":
    sys.exit(main())
