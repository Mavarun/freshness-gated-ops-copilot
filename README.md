# Freshness-gated ops copilot

Ops knowledge copilot that refuses when evidence fails a freshness SLA, grounding
check, retriever-agreement check, **session cost budget**, **prompt-injection
canary** scan, or **PII/secret redaction** gate — and holds mutating **writes**
behind a **HITL approve** gate. Offline CI, frozen clock.

| Decision | Meaning |
| --- | --- |
| `ANSWER` | Fresh supporting evidence passed grounding |
| `REFUSE_STALE` | Supporting chunks older than the SLA |
| `REFUSE_UNGROUNDED` | Related retrieval does not support the ask |
| `REFUSE_NO_EVIDENCE` | Nothing in the corpus matches |
| `REFUSE_DISAGREE` | BM25 and title-hash dense stub disagree on top-k |
| `REFUSE_CANARY` | Extractive draft echoed a planted canary not justified by the query |
| `REFUSE_PII` | Draft contained unauthorized PII/secrets, or a cited doc holds a never-authorizable secret |
| `REFUSE_BUDGET` | Session spent + request `approx_cost_units` would exceed session budget |
| `PROPOSE_WRITE` | Imperative write detected; pending HITL approve (never auto-executes) |



## Held-out synonyms (2026-09-30): the honest synonym number is 0.400

PR #10 reported 0.620 on synonym rows, but its corpus-side map resolved 39 of the
eval's 122 synonym pairs. This slice splits the eval's synonym vocabulary into
**dev** and **held-out**, deletes every held-out word from every product lexicon,
and scores the two groups separately. No golden or paraphrase label changed, and the
203-row set was not regenerated (seed 42, frozen clock 2026-09-13).

**Held-out synonym accuracy: 0.400 (14 of 35 rows).** That number is low, and the
detail makes it worse. All 14 correct held-out rows have a refusal label that fires
without understanding the swapped word (NO_EVIDENCE 6/6, UNGROUNDED 4/4, BUDGET 2/2,
CANARY 1/3, DISAGREE 1/4). On the 12 held-out rows that require the synonym to be
understood (9 ANSWER, 3 PROPOSE_WRITE), the copilot gets **0 of 12**. The config with
no synonym map and no embedding also scores 0.400 on held-out, so nothing in this
repo generalizes to synonyms it has not been given. All misses fail closed.

### What changed

1. **Split** (`synonym_split.py`, `data/golden/synonym_split.json`,
   `scripts/make_synonym_split.py`). The split unit is a *novel replacement word*:
   a content word of the replacement that is not in the key (`feature switch` for
   `feature flag` adds only `switch`). The 127 novel words are shuffled with
   `Random("42|synonym-heldout-split")` and half (64) are held out. A pair is held-out
   if any of its novel words is held out (68 held-out pairs, 63 dev), so the pair sets
   and their vocabularies are disjoint. A synonym row is held-out if any pair it
   applied is held-out (**15 dev rows, 35 held-out**). Applied pairs come from replaying
   the seeded perturber (`perturb.synonym_swap_trace`). The replay must reproduce each
   committed row exactly, or the split fails.
2. **Leakage-free map** (`synonyms.py`). Every held-out word was deleted, including
   standard ops vocabulary: `reboot/bounce/recycle`, `health`, `credential`,
   `config/configuration`, `frequency`, `path`, `affinity`, `flush/purge`,
   `passphrase`, `rollover`, `downtime`, `steps`, `workaround`, `rollout`,
   `objective`. The `response time` and `requests per second` phrases were also
   removed, along with `request rate` (it plural-folds onto the held-out
   `requests`). That leaves 15 groups (24 before), one of them `restart` on its own.
   Tests assert zero held-out words in the map and in the glossary, and that
   `leakage_report` shows held-out coverage **0 of 65** (dev 18 of 57).
3. **Evaluator**. Every synonym row carries its split. The report adds a dev vs
   held-out table and clean-set safety counts. PR #10's run is frozen per row
   (`artifacts/robustness_pr10.json`) and re-scored with the same split.
4. **Semantic backoff** (`semantic.py`, `CopilotConfig.use_semantic_backoff`,
   **default off**). This is a positive-PMI co-occurrence matrix (window 4, 1/distance
   weights, context smoothing 0.75), factorized with numpy SVD to 32 dimensions. It is
   trained on the corpus sentences plus a 40-line generic ops glossary
   (`data/glossary/ops_glossary.txt`), with a char-trigram Dice fallback (at least 0.72
   and a 0.05 margin). It only fires on a word that is still unknown after the synonym
   and typo steps, and it adds at most one corpus word as support. It needs no
   downloads and no API, and it runs in CI. It stays **off** because it did not move
   held-out accuracy (0.400 → 0.400).
5. **Known bugs**. **g42**: the page-oncall cue no longer has to end the query, and
   the target comes from the first `for …` after it. **g28**: an unknown token before
   an auxiliary whose keyboard-slip candidates include a wh-word is read as that
   wh-word (`wat is` → `what is`, not the corpus word `wait`). The write gate uses the
   same rule, so `Hwo do I restart X?` no longer proposes a write.

### Before / after (real runs, same 203 rows)

| metric | before (PR #10) | after: map only (default) | after: map + embedding |
| --- | ---: | ---: | ---: |
| clean decision_accuracy (51) | 1.000 | **1.000** | 1.000 |
| perturbed decision_accuracy (203) | 0.892 | 0.862 | 0.867 |
| synonym, all rows (50) | 0.620 | 0.460 | 0.480 |
| synonym, **dev** rows (15) | 0.733 | 0.600 | 0.667 |
| synonym, **held-out** rows (35) | 0.571 (leaky) | **0.400** | **0.400** |
| word_order / typo / polite | 0.980 / 0.980 / 0.980 | 1.000 / 1.000 / 0.980 | 1.000 / 1.000 / 0.980 |
| flips | 22 | 28 | 27 |
| fail-open, perturbed / clean | 0 / 0 | **0 / 0** | 0 / 0 |
| spurious PROPOSE_WRITE, perturbed / clean | 0 / 0 | **0 / 0** | 0 / 0 |
| raw PII/secret in output, perturbed / clean | 0 / 0 | **0 / 0** | 0 / 0 |

PR #10's held-out column is leaky: its map still contained held-out words. The drop
from 0.892 to 0.862 is the cost of removing that leakage (6 held-out rows and 2 dev
rows flipped to refusals). g28-typo and g42-word_order were fixed.

| gate (expected) | n | PR #10 | after (default) | after (+ embedding) |
| --- | ---: | ---: | ---: | ---: |
| ANSWER | 56 | 0.804 | 0.768 | 0.786 |
| PROPOSE_WRITE | 16 | 0.812 | 0.750 | 0.750 |
| REFUSE_BUDGET | 12 | 1.000 | 1.000 | 1.000 |
| REFUSE_CANARY | 16 | 0.875 | 0.812 | 0.812 |
| REFUSE_DISAGREE | 16 | 0.750 | 0.812 | 0.812 |
| REFUSE_NO_EVIDENCE | 24 | 1.000 | 1.000 | 1.000 |
| REFUSE_PII | 12 | 0.917 | 0.833 | 0.833 |
| REFUSE_STALE | 31 | 0.968 | 0.903 | 0.903 |
| REFUSE_UNGROUNDED | 20 | 1.000 | 1.000 | 1.000 |

Ablation (normalizer, filler, typo tolerance, write cues, and quarantine always on):

| config | clean | perturbed | synonym | syn dev | syn held-out | fail-open | spurious write |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| no map, no embedding | 1.000 | 0.828 | 0.320 | 0.133 | 0.400 | 1 | 0 |
| map only (leakage-free, default) | 1.000 | 0.862 | 0.460 | 0.600 | 0.400 | 0 | 0 |
| embedding only | 1.000 | 0.837 | 0.360 | 0.267 | 0.400 | 1 | 0 |
| map + embedding | 1.000 | 0.867 | 0.480 | 0.667 | 0.400 | 0 | 0 |

The fail-open in the two no-map rows is `g49-synonym` (*slack bot secret*). Without
the dev `token`~`secret` link, the token page stops counting as support. The copilot
then answers from `slack_inc_4821`, which mentions a webhook *secret*. Nothing leaks,
but the label is REFUSE_PII. The embedding does not replace that link.

### Why the embedding does not help held-out

- The corpus has 57 docs, 90 chunks, and about 560 content words. PPMI/SVD neighbours
  are topical, not synonyms: `lag`→kafka/consumer, `timeframe`→maintenance,
  `chargeback`→audit. Only 20 of the 64 held-out words occur in the corpus at all,
  mostly in other senses (`lag` means consumer lag, not latency).
- Held-out words may not appear in the glossary, which a test enforces. So the
  embedding cannot contain any held-out word the corpus lacks.
- Char trigrams find spelling neighbours with the wrong meaning: `maintainer`~container
  0.67, `second`~secondary 0.67, `callback`~rollback 0.62, `interval`~internal 0.62.
  The 0.72 floor was chosen so that none of them fires.
- The single dev gain (`g24`: *timeframe* supported by *maintenance*) happens for the
  topical reason. With 3 neighbours instead of 1, `chargeback`→{audit, payment, …}
  moved the `g22-polite` trap from REFUSE_UNGROUNDED to REFUSE_STALE. That is a latent
  fail-open if the evidence had been fresh. This is why neighbours are capped at 1, the
  flag is off, and a test pins the trap while the flag is on.

### Remaining flips (28)

- **21 held-out synonym rows**, all fail-closed. Among them: *present … lag*, *switch
  turned on*, *left … allowance*, *health*, *release steps*, *burn down*, *kick off*,
  *requests per second*, *negotiation*, *affinity seed*, *flush point frequency*,
  *system … address*, *purge … credential*, *cycling timetable*, *bounce*, *reboot*,
  *on-duty engineer … downtime*, *cycling maintainer*, and *timetable timeframe*.
- **6 dev synonym rows**:
  - `g02` *lead on-duty*: `on-duty` is hyphenated, so it is exact-only.
  - `g24` *timeframe*: fixed only with the embedding on.
  - `g35` *location*.
  - `g39` *route*: the `path`~`route` group went because `path` is held out.
  - `g43` *update … setting*: `update` is deliberately not a patch verb.
  - `g48`: `secret`~`credential` is gone, so it refuses UNGROUNDED instead of PII. It
    still refuses and leaks nothing.
- `g05-polite`: *"I was wondering"* still flips BM25 top-1 and triggers
  REFUSE_DISAGREE (unchanged).

### Weaknesses

- **Held-out answer/write recall is 0 of 12.** Real synonym robustness needs lexical
  knowledge that this repo does not have offline. WordNet and model downloads are out
  of scope. The honest next step is a versioned ops thesaurus written by someone who has
  not seen the eval, or a paraphrase set written by other people.
- The split is lopsided: 15 dev rows vs 35 held-out, because a two-pair row is held-out
  if either pair is. With n=15, one dev row moves the score by 0.067.
- Removing held-out words cost real ops knowledge. `reboot X` and `bounce X` now refuse
  instead of proposing a restart. That is safe but worse for users. Several gates
  dropped relative to PR #10.
- The glossary was written after the split existed, so any dev word in it makes the dev
  numbers optimistic. Held-out words are excluded by test.
- The g28 rule only handles wh-words before an auxiliary. The write-gate version also
  snaps without a vocabulary (`hwo do` → `how do`), which can only remove writes.
- There is still one variant per type per case, and the split and the perturber share
  seed 42.

## Robust grounding (2026-09-28): 0.473 → 0.892 on the same 203 rows

*History. PR #10 measured 0.892 perturbed and 0.620 synonym with a map that covered
39 of the eval's 122 synonym pairs. The 09-30 section above removes that leakage.
PR #10's full numbers are frozen in `artifacts/robustness_pr10.json`.* The ablation
at the time put the leakage-free floor (normalizer + salience only) at 0.645.

### What changed

1. **One normalizer** (`text.normalize_text`: NFKC + accent strip, lowercase, curly
   quotes/dashes folded, loose punctuation stripped, identifier punctuation kept) used
   by BM25, the body TF-IDF, the title-hash dense stub (titles *and* queries), grounding,
   the write gate, and the PII contact allowlist. `p99?` and `p99` are now the same term.
2. **Salience**: `FILLER_WORDS` (politeness/discourse: *hey, team, sorry, bother,
   wondering, quick, question, kindly, …*) plus a few more function words are never salient.
   Identifiers, numbers, and corpus-known words are salient. **Unknown content words
   still count as missing** (`millicore`, `chargeback`, `SAP`), because the traps depend on it.
3. **Typo tolerance** (`lexicon.py`): an unknown plain word snaps to a *unique* corpus
   word within Damerau-Levenshtein 1, and the edit must be a keyboard slip (transposition,
   dropped letter, doubled or QWERTY-adjacent extra letter, adjacent-key substitution).
   Tokens of 3-4 characters must also keep their first and last letters. Identifiers are
   exact-only. Plain distance-1 matching broke two clean cases (`interval`→`internal`,
   `patch`→`path`), and the keyboard rule rejects both. Typo'd filler (`whhat`, `crrent`)
   is dropped.
4. **Corpus-side synonym/lemma map** (`synonyms.py`, 24 groups then, 15 after the
   09-30 held-out split, each anchored on a corpus term): a query word is supported
   by any word in its group, and hyphen spellings match (`oncall`~`on-call`). It is
   separate from `perturb.OPS_SYNONYMS` and never imports it (a test enforces this).
   Ambiguous pairs from the eval map were left out on purpose (`lag`, `owner`~`contact`,
   `key`~`secret`, `seed`~`salt`, `live`~`prod`). `db`~`database` was tried and removed
   because it moved a clean trap from NO_EVIDENCE to UNGROUNDED.
5. **Write intent**: the *how do I / how to / what is / steps to / procedure for*
   exemption now matches anywhere in the query, and "how" may sit up to two words before
   its auxiliary. `reboot/bounce/recycle` counted as restart until the 09-30 split
   held them out. Slips of 5+ characters in write keywords (`rrstart`, `pathc`,
   `onclal`) are read as the keyword.
6. **Fail-open guard**: the PII gate now also refuses when a cited *document*
   holds a never-authorizable secret (AWS key, Slack token) that the extractive draft
   happened to skip. This closed the old `g49-synonym` fail-open and a new one
   (`g48-synonym`) that the synonym map had exposed.

## Robustness eval (2026-09-27): where the 1.000 breaks

*Pre-fix baseline, kept for history. The 09-28 and 09-30 slices above build on it.*

The 51-case golden set is hand-crafted, so its 1.000 says little about real users.
This slice perturbs every golden query (same label, no re-tuning) and reports the drop.

### Hypothesis

1. Paraphrased and typo'd versions of the golden queries will lower decision_accuracy below 1.000, mostly through BM25 synonym misses and keyword-exact gates (write intent, PII allowlist).
2. A per-gate breakdown will show which gates are brittle (expect write-intent and PII allowlist to be worst).
3. Reporting the drop, instead of hiding it, is the point; do not tune the golden labels to recover 1.000.

### Method (offline, seeded, no LLM)

`perturb.py` builds four perturbations per golden case with seed 42 (RNG keyed on
`seed|kind|query`, so output is byte-stable): **synonym** (1-2 swaps from a ~65-entry
hand-written ops map, e.g. restart→bounce, latency→lag), **word_order** (disjoint
adjacent-token swaps inside a clause; first token fixed), **typo** (1-2 char edits on
plain words ≥4 chars; identifiers like `checkout-api`, `p99`, `CNRY-*` untouched),
**polite** ("Could you please tell me …", "Quick question: …"). Perturbations that
leave a query unchanged are dropped (1 synonym row), giving **203** rows in
`data/golden/paraphrase_questions.jsonl`. Budget-trap rows carry their `session_id`
and seeded spend.

### Results (real run, frozen clock 2026-09-13, seed 42)

Clean golden scored 1.000 and perturbed scored **0.473** (96/203): synonym 0.320,
word_order 0.941, typo 0.294, polite 0.333. Of the 107 flips, 101 landed on
`REFUSE_UNGROUNDED`, with 1 labelled fail-open and 2 spurious write proposals. The main
cause was the lexical grounding gate, not BM25: smoothed IDF scored typos and polite
filler as high-weight "missing" terms. Write intent was brittle because the how-to cue
was anchored at `^`. No golden label was changed. The frozen summary is in
`artifacts/robustness_baseline.json` and remains the fail-open ceiling in the tests.

Weaknesses of this eval: one variant per type per case (no seed sweep), a hand-written
synonym map sized to this corpus, typos never touching identifiers, and word-order swaps
that are a stress test rather than natural paraphrase.

## Hypothesis (2026-09-19 prompt-injection canary farm)

1. Plant unique `CNRY-*` canary tokens in a subset of corpus docs; if an extractive
   answer echoes a canary that is **not** present in the query, policy emits
   `REFUSE_CANARY` (exfiltration / prompt-injection signal).
2. Queries that should not need those docs must not surface canaries in answers
   (clean controls stay `ANSWER` with empty canary leak sets).
3. Golden cases labeled with `expect_canary_leak` show canary-detection
   **precision / recall / F1** on the frozen offline eval.

Policy order (after budget): no-evidence → ungrounded → stale → disagree → grounding →
**canary** → answer. Canary token values are withheld from refusal text.

### Canary metrics (frozen clock 2026-09-13)

| Metric | Value |
| --- | ---: |
| canary_precision | 1.000 |
| canary_recall | 1.000 |
| canary_f1 | 1.000 |
| n_canary_labeled | 6 |
| decision_accuracy (full golden) | 1.000 |

Weaknesses: exact-string canaries (not paraphrased exfiltration); extractive path must
pull the planted sentence; justified queries must literally name the token; lexical
bleed from canary docs can nudge nearby no-evidence boundaries.



## Hypothesis (2026-09-21 HITL write gate)

1. Read-path `ANSWER` is fine; any proposed *write* (restart service, page oncall,
   patch config) must stay **PENDING** until explicit human approve.
2. Audit log records `propose → approve|reject` with **actor + timestamp**;
   **rejected writes never execute** (execute stub is hard-gated on `APPROVED`).
3. Golden + API tests prove writes cannot execute without approve.

Policy: after the session budget gate, write-intent heuristics emit `PROPOSE_WRITE`
instead of answering or mutating. How-to reads (`How do I restart…`) do **not** trip
the write gate. Existing freshness / disagreement / canary / budget gates stay intact
for the read path.

### HITL audit story

```
query with write intent
  -> budget gate (may REFUSE_BUDGET)
  -> detect_write_intent (restart|page_oncall|patch_config)
  -> HitlWriteLedger.propose  status=PENDING  audit+=propose(actor, ts)
  -> decision PROPOSE_WRITE  (no side effects)

POST /writes/{id}/approve {actor}
  -> audit+=approve → execute_stub → status=EXECUTED

POST /writes/{id}/reject {actor}
  -> audit+=reject → status=REJECTED  executed=false forever
```

### HITL metrics (frozen clock 2026-09-13)

| Metric | Value |
| --- | ---: |
| propose_write_rate | 0.087 |
| n_propose_write | 4 |
| decision_accuracy (full golden) | 1.000 |
| pytest | 110 passed |

Weaknesses: keyword/heuristic write detection (not an LLM planner); in-memory HITL
ledger is process-local; execute path is an offline stub (no real k8s/pager/config
side effects); polite paraphrases outside the regexes will miss.


## Hypothesis (2026-09-22 PII / secret redaction gate)

1. Extractive answers can leak emails, API keys, and phone numbers planted in ops
   docs; a post-answer scanner must **redact** or emit `REFUSE_PII`.
2. Queries that *explicitly* ask for a rotation contact email (keyword allowlist)
   may receive a **masked** contact form — never the raw address. AWS-like keys and
   Slack tokens **never** authorize.
3. Golden cases labeled with `expect_pii` prove PII-detection **precision / recall / F1**
   independently of freshness/canary.

**Policy (clear):** unauthorized email/phone in the draft → `REFUSE_PII`. Allowlisted
contact queries → `ANSWER` with masked values (`o***@example.com`, `***-***-2890`).
Any `aws_key` / `slack_token` match → always `REFUSE_PII`. Existing freshness /
disagreement / canary / budget / HITL gates stay intact; PII runs after canary.

### PII metrics (frozen clock 2026-09-13)

| Metric | Value |
| --- | ---: |
| pii_precision | 1.000 |
| pii_recall | 1.000 |
| pii_f1 | 1.000 |
| n_pii_labeled | 5 |
| decision_accuracy (full golden) | 1.000 |
| pytest | 110 passed |

Weaknesses: regex detectors (no NER); phone patterns are US/E.164-biased; authorize
allowlist is keyword-exact; corpus bleed can nudge nearby no-evidence/ungrounded
boundaries; secrets refusal does not attempt partial mask-and-answer.

## Hypothesis (2026-09-20 session cost budget)

1. Production agents need a hard session cost budget; exceeding it must `REFUSE_BUDGET` **before answering**.
2. Traces already carry `approx_cost_units` — accumulate per `session_id` and gate in policy.
3. Golden + API tests prove budget trips **independently** of freshness/disagreement.

Prior (2026-09-16): disagreement routing. Prior (2026-09-15): FastAPI. Prior (2026-09-14): per-source SLAs.

## Architecture (budget → HITL write → retrieve gates → canary → PII)

```
query (+ optional session_id)
  -> normalize_text (shared by every ranker and gate)
  -> budget gate (REFUSE_BUDGET if spent + cost > budget)
  -> write-intent heuristic → PROPOSE_WRITE (HitlWriteLedger PENDING)
  -> else rewrite_query (drop filler, snap typos/unknown synonyms to corpus words)
  -> retrieve BM25 + TitleHashDenseStub on the rewritten query
  -> support / freshness / disagreement / grounding (salient terms, typo + synonym aware)
  -> canary scan on extractive draft (REFUSE_CANARY on unjustified echo; raw query)
  -> PII scan (REFUSE_PII, secret-bearing cited doc → REFUSE_PII, or mask contacts)
  -> ANSWER | REFUSE_*
  -> record cost on session ledger
```

Defaults: `use_budget_gate=True`, `session_budget_cost_units=5.0`; `use_canary_gate=True`; `use_hitl_write_gate=True`; `use_pii_gate=True`; `typo_tolerance=True`; `use_synonyms=True`.

## Package

```
src/ops_copilot/
  text.py            normalize_text, tokenize, STOPWORDS + FILLER_WORDS, is_identifier
  lexicon.py         CorpusVocabulary + keyboard-slip typo correction (DL <= 1)
  synonyms.py        corpus-side ops equivalence groups + phrase/hyphen folding
  grounding.py       salient QueryTerms, IDF coverage + key-term gate
  write_actions.py   ProposedWrite schema + detect_write_intent heuristics
  hitl.py            HitlWriteLedger propose/approve/reject/execute_stub + audit
  canary.py          CanaryRegistry + scan_answer / canary_detection_metrics
  pii.py             PII/secret detector patterns (email/phone/AWS/Slack)
  pii_redact.py      mask helpers + scan_answer_pii authorize/refuse policy
  cost_budget.py     SessionCostLedger (spent/record/seed/would_exceed)
  policy.py          … → REFUSE_CANARY → REFUSE_PII → ANSWER
  pipeline.py        ask(...); HITL propose; PII scan/redact on draft
  eval.py            golden + canary/pii P/R/F1 + budget + propose_write rates
  api.py             POST /query (+ pii_detected, redactions_count) + HITL writes
  perturb.py         seeded synonym / word-order / typo / polite perturbations
  paraphrase_set.py  build/load perturbed golden rows (labels preserved)
  robustness.py      clean vs perturbed per perturbation/gate, fail-open, ablation, leakage
data/canaries/       offline CNRY registry
data/corpus/canary_docs.jsonl
data/corpus/pii_docs.jsonl
data/golden/paraphrase_questions.jsonl   203 perturbed rows (generated)
artifacts/robustness_baseline.json       frozen PR #9 robustness summary (before)
```

## How to run

```bash
python -m pip install -e ".[dev,api]"
pytest
python scripts/run_eval.py
python scripts/make_paraphrase_set.py   # regenerate perturbed set (seed 42)
python scripts/run_robustness.py        # report + metrics: before/after, ablation, leakage
python scripts/run_api.py
```

## Golden eval (real run — 2026-09-22 PII redaction gate)

51 labeled cases on frozen clock `2026-09-13T00:00:00+00:00`.

| Metric | Per-source + disagreement + budget + canary + HITL + PII |
| --- | ---: |
| cases | 51 |
| decision_accuracy | 1.000 |
| refusal_precision | 1.000 |
| refusal_recall | 1.000 |
| answer_grounding_rate | 1.000 |
| disagreement_rate | 0.275 |
| n_disagreed | 14 |
| budget_refuse_rate | 0.059 |
| n_budget_refused | 3 |
| canary_precision | 1.000 |
| canary_recall | 1.000 |
| canary_f1 | 1.000 |
| n_canary_labeled | 6 |
| propose_write_rate | 0.078 |
| n_propose_write | 4 |
| pii_precision | 1.000 |
| pii_recall | 1.000 |
| pii_f1 | 1.000 |
| n_pii_labeled | 5 |

`pytest`: **110 passed** (96 prior + 14 PII redaction-gate).

`pytest` after the robustness slice: **133 passed** (110 prior + 23 perturbation/paraphrase/robustness).

`pytest` after robust grounding: **231 passed** (133 prior + 98 normalizer / salience / typo /
synonym / write-cue / fail-open-guard tests).

`pytest` after the held-out synonym slice: **269 passed**. Of those, 38 are net new: the
split and held-out leakage tests, the semantic backoff and its no-fail-open guard,
g28/g42, dev vs held-out reporting, and zero-safety-count guards. Tests that encoded
held-out pairs (`health`~`status`, `bounce`/`reboot` as restart) now assert a refusal.

CI: `.github/workflows/eval.yml` runs pytest + `scripts/run_eval.py` on push/PR to main, then
`scripts/run_robustness.py` as a report step. That step fails only on a crash, never on an accuracy drop.

## Limitations

- Lexical grounding is not entailment; title-hash dense stub is not a real encoder.
- Exact-string canaries miss paraphrased exfiltration; justified queries must name the token.
- In-memory session ledger is process-local (demo API, not multi-tenant Redis).
- In-memory HITL write ledger is process-local; execute path is an offline stub.
- Write-intent detection is keyword/heuristic (misses paraphrases outside regexes such as *on-duty engineer* or *update … setting*).
- Approx cost units are heuristic, not dollar billing.
- Regex PII detectors (no NER); authorize allowlist is phrase-exact on normalized text; US/E.164 phone bias.
- Secrets always refuse (no mask-and-answer path for AWS/Slack tokens).
- Synthetic corpus / frozen clock; crafted golden set (1.000 scores are a harness, not prod claim).
- Under seeded perturbations decision_accuracy is 0.862 with a leakage-free synonym map (0.892 in PR #10 with a leaky one). **Held-out synonym accuracy is 0.400, and 0 of 12 held-out rows that need an answer or a write succeed.** Synonyms the repo has not been given are not understood; they fail closed.

## Hiring takeaway

Production agents need a refusal contract: evidence age, ranker agreement, grounding,
session spend, injection canaries, PII/secret redaction, **and HITL for mutating writes**. Review
`policy.py`, `hitl.py`, `write_actions.py`, `canary.py`, `pii.py`, `cost_budget.py`, and
`data/golden/questions.jsonl`.

## License

MIT. Author: M.Varun (`116015799+Mavarun@users.noreply.github.com`).
