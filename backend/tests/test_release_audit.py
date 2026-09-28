"""P08: the release audit's licence classification and reviewed-exception matching."""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "release_audit.py"
spec = importlib.util.spec_from_file_location("release_audit", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_licence_expressions_are_classified_by_their_most_restrictive_requirement():
    cases = {
        "MIT": "PERMISSIVE",
        "MIT OR GPL-3.0-only": "PERMISSIVE",  # the permissive option may be chosen
        "(MIT OR Apache-2.0) AND GPL-3.0-only": "COPYLEFT",  # every AND term applies
        "BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0": "PERMISSIVE",
        "MIT and MPL-2.0": "WEAK_COPYLEFT",
        "LGPL-3.0-only": "WEAK_COPYLEFT",
        "AGPL-3.0-or-later": "COPYLEFT",
        "Some custom licence": "REVIEW",
        None: "UNKNOWN",
    }
    assert {text: audit.classify(text) for text in cases} == cases


def test_only_the_reviewed_exceptions_are_accepted():
    def package(ecosystem, name, licence):
        return {"ecosystem": ecosystem, "name": name, "license": licence}

    assert audit.accepted(package("PyPI", "psycopg", "LGPL-3.0-only"))
    assert audit.accepted(package("npm", "lightningcss-linux-x64-gnu", "MPL-2.0"))
    assert audit.accepted(package("PyPI", "psycopg", "GPL-3.0-only")) is None  # licence changed
    assert audit.accepted(package("npm", "left-pad", "MPL-2.0")) is None


REVIEW_SCRIPT = SCRIPT.with_name("public_release_review.py")
review_spec = importlib.util.spec_from_file_location("public_release_review", REVIEW_SCRIPT)
review = importlib.util.module_from_spec(review_spec)
review_spec.loader.exec_module(review)


def test_public_review_recognises_the_credentials_this_project_uses():
    # Built at run time so this file itself never contains a matching string.
    key, word = "A1b2" * 8, "s3cr3t-" + "value9"
    positives = [
        "FIRMS_MAP_KEY=" + key,
        "https://firms.modaps.eosdis.nasa.gov/api/data_availability/csv/" + key + "/ALL",
        "?MAP_KEY=" + key,
        "POSTGRES_PASSWORD=" + word,
        "postgresql+psycopg://thermoscope:" + "abc" + "@127.0.0.1:55432/db",
        "tsr_" + "x" * 43,
        "eyJ" + "a" * 12 + "." + "b" * 12 + "." + "c" * 12,
        "gh" + "p_" + "Z" * 36,
        "github_" + "pat_" + "Y" * 40,
        "-----BEGIN " + "RSA PRIVATE KEY-----",
    ]
    negatives = [
        "POSTGRES_PASSWORD: disposable-ci-only",
        'f"postgresql+psycopg://thermoscope:{password}@127.0.0.1"',
        "postgresql+psycopg://test:private-test-password@127.0.0.1:1/test",
        "TOKEN = re.compile(r'tsr_...')",
        "POSTGRES_PASSWORD=",
        "ANNOTATION_TOKEN is no longer read",
        'const TOKEN_KEY = "thermoscope.reviewer-token";',
        "POSTGRES_PASSWORD=\nOBJECT_STORE_LOCAL_PATH=./local/objects",
        'DB_SECRET = "' + "Sentinel-db-pass-8Qx2" + '"',
    ]
    for text in positives:
        assert review.CREDENTIAL.search(text.encode()), text[:12]
    for text in negatives:
        assert not review.CREDENTIAL.search(text.encode()), text
    assert review.LOCAL_PATH.search(("/" + "home/someone/project").encode())
    assert review.category("docs/tasks/x.md") == "process record"
    assert review.category(review.REPORT) == "this release review"


def test_audit_exit_codes_separate_vulnerabilities_licences_sources_and_drift(
    monkeypatch, tmp_path
):
    def run(vulns, licence, fail=False, lockfile_version="1.0"):
        monkeypatch.setattr(audit, "python_packages",
                            lambda _: [{"ecosystem": "PyPI", "name": "pytest",
                                        "version": lockfile_version}])  # fmt: skip
        monkeypatch.setattr(audit, "npm_packages", lambda _: [
            {"ecosystem": "npm", "name": "x", "version": "1", "license": licence,
             "scope": "runtime"}])  # fmt: skip

        def osv(packages):
            if fail:
                raise audit.SourceUnavailable("OSV query failed: URLError")
            return [vulns, []]

        monkeypatch.setattr(audit, "osv", osv)
        return audit.main(["--out", str(tmp_path / "audit.json")])

    installed = __import__("importlib.metadata").metadata.version("pytest")
    assert run([], "MIT", lockfile_version=installed) == 0
    assert run(["GHSA-test"], "MIT", lockfile_version=installed) == 10
    assert run([], "GPL-3.0-only", lockfile_version=installed) == 11
    assert run([], "MIT", fail=True, lockfile_version=installed) == 12
    assert run([], "MIT", lockfile_version="0.0.1") == 13
