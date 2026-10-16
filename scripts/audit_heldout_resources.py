#!/usr/bin/env python3
"""List held-out synonym words found in hand-written data resources (should be none)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ops_copilot.resource_audit import audit  # noqa: E402

if __name__ == "__main__":
    res = audit()
    print(json.dumps(res, indent=2, sort_keys=True))
    raise SystemExit(1 if any(res.values()) else 0)
