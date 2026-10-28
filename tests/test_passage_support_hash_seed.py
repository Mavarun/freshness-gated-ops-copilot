"""Passage-support scores must not depend on PYTHONHASHSEED.

The passage words used to be iterated in ``set`` order, so float32 sums (and
best-match ties) changed with the interpreter's hash seed: CI on PR #32 saw
0.99165200 vs 0.99165201 in the null-pool fallback test. Passage words are now
de-duplicated in passage order. This runs the same scores under three hash
seeds in fresh interpreters and asserts they are bit-identical.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SNIPPET = r"""
import json
from ops_copilot.corpus import Corpus
from ops_copilot.passage_support import PassageSupportModel, pair_features, substitution_probs
from ops_copilot.qa_translation import words
m = PassageSupportModel.load()
p = words(next(c.text for c in Corpus().chunks if "error budget" in c.text.lower()))
w = lambda x: 1.0
q = ["what", "flavour", "checkout", "error", "budget"]
out = {
    "absent": [float(x).hex() for x in substitution_probs(m, q, "absent", p, w, ["alpha", "beta"])],
    "fallback": [float(x).hex() for x in substitution_probs(m, q, "flavour", p, w, ["checkout", p[0], "budget"])],
    "verdict": float(m.verdict(q, p, w).prob).hex(),
    "features": {k: float(v).hex() for k, v in pair_features(q, p, w, m.vectors).items()
                 if isinstance(v, (int, float))},
}
print(json.dumps(out, sort_keys=True))
"""


def _run(seed: str) -> dict:
    env = {**os.environ, "PYTHONHASHSEED": seed,
           "PYTHONPATH": str(ROOT / "src") + os.pathsep + os.environ.get("PYTHONPATH", "")}
    res = subprocess.run([sys.executable, "-c", SNIPPET], cwd=ROOT, env=env,
                         capture_output=True, text=True, check=True)
    return json.loads(res.stdout.strip().splitlines()[-1])


def test_scores_are_bit_identical_across_hash_seeds():
    # seeds 0, 2 and 3 all failed the 1e-12 fallback check before the fix
    runs = [_run(s) for s in ("0", "2", "3")]
    assert runs[0]["features"]  # the snippet really scored something
    assert runs[0] == runs[1] == runs[2]
