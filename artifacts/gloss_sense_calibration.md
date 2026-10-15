# Gloss-sense calibration (Wiktionary computing verb gloss bridges)

Clean golden: 51 rows via ``run_eval``. Verb list: 20 hand-written verbs in ``data/write/gloss_sense_dev.jsonl`` (no ontology verbs, no held-out words). Held-out synonym rows are not scored.

Backoff off: clean 1.000, verb-list accuracy 0.850 (every verb predicted ``none``).

Chosen: min_score **3.0**, margin **0.4**, min_gloss_cosine **0.5** (clean 1.000, verb-list 1.000; 60 of 60 settings clear the safety bar). Calibration candidate for default-on: **True**. The held-out run is the go / no-go.

## Verb list (chosen setting)

| verb | kind | label | predicted | score | ok |
| --- | --- | --- | --- | ---: | --- |
| reload | service | restart_service | restart_service | 3.0635 | yes |
| activate | flag | toggle_flag | toggle_flag | 3.607 | yes |
| tweak | config_key | patch_config | patch_config | 3.0162 | yes |
| rerun | service | none | none | 0.0 | yes |
| refresh | service | none | none | 0.0 | yes |
| trace | service | none | none | 0.0 | yes |
| audit | service | none | none | 0.0 | yes |
| grep | service | none | none | 0.0 | yes |
| query | service | none | none | 0.0 | yes |
| debug | service | none | none | 0.0 | yes |
| profile | service | none | none | 0.0 | yes |
| nuke | service | none | none | 0.0 | yes |
| zap | service | none | none | 0.0 | yes |
| love | service | none | none | 0.0 | yes |
| thank | service | none | none | 0.0 | yes |
| delete | service | none | none | 0.0 | yes |
| destroy | service | none | none | 0.0 | yes |
| upscale | service | none | none | 0.0 | yes |
| shrink | service | none | none | 0.0 | yes |
| summon | recipient | none | none | 0.0 | yes |
