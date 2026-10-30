"""Exact exemption list of the repo's own multi-part identifiers (off by default)."""

from __future__ import annotations

from ops_copilot.passphrase import CUED_PASSPHRASE, CuedPassphraseDetector, known_identifiers
from ops_copilot.passphrase_tail_protocol import data_identifiers


def test_list_covers_every_protocol_identifier_and_is_lower_case() -> None:
    ids = known_identifiers()
    assert set(data_identifiers()) <= ids
    assert all(i == i.lower() for i in ids)
    assert "sidecar-mesh-mtls-handshake-budget" in ids and "cache.flush.orchestrator" in ids


def test_list_never_reads_the_gzipped_wordlist() -> None:
    import re

    from ops_copilot.passphrase_wordlist import eff_words

    eff = set(eff_words())
    parts = [re.split(r"[-._]", i) for i in known_identifiers()]
    # no 4+ part name made only of EFF words, which a read of the wordlist would add
    assert not [p for p in parts if len(p) >= 4 and all(w in eff for w in p)]


def test_exemption_is_on_by_default_and_exact() -> None:
    assert CUED_PASSPHRASE.exempt_identifiers is True
    # the Oct 29 identifier failure: arm on compounds flags a known doc id
    on = CuedPassphraseDetector(coherence_compounds=True, exempt_identifiers=False)
    ex = CuedPassphraseDetector(coherence_compounds=True, exempt_identifiers=True)
    text = "api key sidecar-mesh-mtls-handshake-budget"
    assert on.search(text) is not None
    assert ex.search(text) is None
    assert ex.search("api key SIDECAR-MESH-MTLS-HANDSHAKE-BUDGET") is None
    # a trailing number part does not defeat the list
    assert ex.search("api key sidecar-mesh-mtls-handshake-budget-2") is None
    # exact only: one changed part is not exempt
    assert ex.search("api key sidecar-mesh-mtls-handshake-budgets") is not None


def test_exemption_never_touches_space_runs() -> None:
    ex = CuedPassphraseDetector(exempt_identifiers=True)
    text = "the deploy token marble meadow lagoon badger stopped working"
    assert ex.search(text).group() == CUED_PASSPHRASE.search(text).group()
