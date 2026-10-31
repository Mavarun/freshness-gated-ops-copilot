"""The committed attached_digit one-shot check: it fails one pre-registered check and ships off."""

from __future__ import annotations

import json
from pathlib import Path

from ops_copilot import passphrase_digit_protocol as D
from ops_copilot.passphrase import CUED_PASSPHRASE
from ops_copilot.passphrase_wordlist import score_rows, wordlist_passphrases

ART = Path(__file__).resolve().parents[1] / "artifacts" / "passphrase_digit_check.json"


def test_artifact_numbers_and_decision() -> None:
    out = json.loads(ART.read_text())
    a, s = out["attached"], out["standard"]
    assert (a["seed"], s["seed"]) == (D.ATTACHED_SEED, D.STANDARD_SEED)
    assert (a["shipped"]["leak_words"], a["candidate"]["leak_words"]) == (1857, 7)
    assert (a["shipped"]["over_words"], a["candidate"]["over_words"]) == (507, 581)
    assert s["shipped"] == s["candidate"]
    tr, te = out["se"]["train"], out["se"]["test"]
    assert (tr["sent_shipped"], tr["sent_candidate"], tr["ident_new"], tr["n_identifiers"]) == (28, 29, 12, 1920)
    assert (te["sent_shipped"], te["sent_candidate"], te["ident_new"], te["n_identifiers"]) == (0, 0, 1, 147)
    assert D.checks(out) == out["checks"]
    assert [k for k, v in out["checks"].items() if not v] == ["se_train_identifiers"]
    assert out["ships"] is False
    # the unguarded knob never shipped; Oct 31 ships it only behind digit_guard
    assert CUED_PASSPHRASE.attached_digit is True and CUED_PASSPHRASE.digit_guard is True


def test_probe_side_reproduces_offline() -> None:
    out = json.loads(ART.read_text())
    rows = wordlist_passphrases(D.ATTACHED_SEED, D.N_ROWS, number_style="attached")
    assert score_rows(rows, D.patterns_with(D.candidate_detector()))["total"] == out["attached"]["candidate"]
