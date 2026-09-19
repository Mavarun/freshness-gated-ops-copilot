"""Golden-set runner — assembled from _eval_part*.py fragments."""
from __future__ import annotations

from pathlib import Path as _Path

__file__ = str(_Path(__file__).resolve())
_parts = [
    _Path(__file__).with_name(f"_eval_part{i}.py").read_text(encoding="utf-8")
    for i in range(3)
]
exec("".join(_parts), globals())
del _parts, _Path
