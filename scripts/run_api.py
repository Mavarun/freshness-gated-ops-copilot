#!/usr/bin/env python3
"""One-command FastAPI demo for the freshness-gated ops copilot.

  python scripts/run_api.py
  # then: curl -s localhost:8000/health | jq
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the ops-copilot FastAPI demo")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "uvicorn is required. Install with: pip install -e '.[api]' "
            "or pip install uvicorn fastapi"
        ) from exc

    print(f"Serving ops-copilot API on http://{args.host}:{args.port}")
    print("  GET  /health")
    print("  GET  /sources")
    print("  POST /query   {\"query\": \"...\", \"clock\": optional ISO}")
    uvicorn.run(
        "ops_copilot.api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
