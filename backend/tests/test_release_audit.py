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
