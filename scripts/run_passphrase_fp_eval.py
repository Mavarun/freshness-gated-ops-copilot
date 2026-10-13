"""False positives of the cued-passphrase detector on outside Stack Exchange text.

    python scripts/run_passphrase_fp_eval.py --raw-dir /tmp/se_qa_raw

Every sentence of the question titles and (first two) answers of the QA
snapshot that contains a credential noun followed by a word run
(``passphrase.CUED_RE``) is a candidate. None of them is a real passphrase
(the posts are public), so every flag is a false positive. Both splits are
reported. Neither is blind: one look at the test split (7 of 269 sentences
flagged, scanning the first 2,000 characters of each answer) prompted adding
``text.STOPWORDS`` to the stop list, and the train split was only scanned
after that change. Needs the raw pages (not in CI); writes
``artifacts/passphrase_fp_eval.{json,md}``.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.passphrase import CUED_PASSPHRASE, CUED_RE  # noqa: E402
from ops_copilot.qa_translation import clean_markdown, is_test  # noqa: E402

ART = ROOT / "artifacts"
_SENT = re.compile(r"(?<=[.!?])\s+|\n+")


def scan(raw_dir: Path) -> dict:
    out = {s: {"sentences": 0, "flagged": 0, "examples": []} for s in ("train", "test")}
    for f in sorted(raw_dir.glob("*.json.gz")):
        site = f.name.split("-")[0]
        for q in json.loads(gzip.decompress(f.read_bytes())).get("items", []):
            split = "test" if is_test(site, int(q["question_id"])) else "train"
            texts = [q.get("title", "")] + [clean_markdown(a.get("body_markdown", "")) for a in (q.get("answers") or [])[:2]]
            for t in texts:
                for sent in _SENT.split(t):
                    if not CUED_RE.search(sent):
                        continue
                    out[split]["sentences"] += 1
                    hits = [m.group() for m in CUED_PASSPHRASE.finditer(sent)]
                    if hits:
                        out[split]["flagged"] += 1
                        if len(out[split]["examples"]) < 10:
                            out[split]["examples"].append({"site": site, "flagged": hits})
    for v in out.values():
        v["rate"] = v["flagged"] / v["sentences"] if v["sentences"] else 0.0
    return out


def render_md(out: dict) -> str:
    lines = [
        "# Cued-passphrase detector: false positives on outside Stack Exchange text",
        "",
        "Sentences with a credential noun followed by a word run, from public question titles and answers "
        "(none is a real secret, so every flag is a false positive). Neither split is blind: one earlier look at "
        "the test split (7 of 269 flagged, first 2,000 characters of each answer) prompted adding "
        "`text.STOPWORDS` to the stop list; the train split was only scanned after that change.",
        "",
        "| split | candidate sentences | flagged | rate |",
        "| --- | ---: | ---: | ---: |",
    ]
    for s, v in out.items():
        lines.append(f"| {s} | {v['sentences']:,} | {v['flagged']} | {v['rate']:.3f} |")
    lines += ["", "Flagged spans on the test split (the words that would be redacted):", ""]
    lines += [f"- {e['site']}: " + ", ".join(f"`{h}`" for h in e["flagged"]) for e in out["test"]["examples"]]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", type=Path, required=True)
    out = scan(ap.parse_args().raw_dir)
    ART.mkdir(exist_ok=True)
    (ART / "passphrase_fp_eval.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    (ART / "passphrase_fp_eval.md").write_text(render_md(out))
    for s, v in out.items():
        print(f"{s:5s} candidate sentences {v['sentences']:5d} flagged {v['flagged']:3d} rate {v['rate']:.3f}")


if __name__ == "__main__":
    main()
