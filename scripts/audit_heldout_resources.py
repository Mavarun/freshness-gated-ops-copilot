#!/usr/bin/env python3
"""List held-out synonym words found in hand-written data resources (should be none),
and check that query-built external snapshots were queried with corpus words only."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ops_copilot.resource_audit import audit, query_problems  # noqa: E402

if __name__ == "__main__":
    res = audit()
    queries = query_problems()
    print(json.dumps({"hand_written": res, "queried_external": queries}, indent=2, sort_keys=True))
    bad = any(res.values()) or any(v for q in queries.values() for v in q.values())
    raise SystemExit(1 if bad else 0)
