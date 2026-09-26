"""Report dependency state without printing settings or credentials."""

import json
import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from thermoscope.config import Settings  # noqa: E402
from thermoscope.database import check_readiness  # noqa: E402

try:
    settings = Settings()
    checks = check_readiness(settings)
except Exception:
    raise SystemExit(
        "Configuration invalid. Check .env against .env.example; values withheld."
    ) from None
print(json.dumps({"platform": platform.system(), "architecture": platform.machine(), **checks}))
raise SystemExit(0 if all(value == "ok" for value in checks.values()) else 1)
