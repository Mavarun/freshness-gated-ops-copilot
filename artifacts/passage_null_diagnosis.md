# Null-control margins on rescue-dependent rows (post-hoc, selects nothing)

43 keep rows (correct only with the rescue) and 6 trap rows (a must-refuse or attribute-trap row the rescue opens), final grounding call, 100 controls.

| id | kind | rescue | logit | control median | margin |
| :--- | :--- | :--- | ---: | ---: | ---: |
| at-07 | trap | `price<-percent` | 2.24 | 2.66 | -0.42 |
| d5-38 | trap | `colour<-default` | 2.29 | 2.66 | -0.37 |
| d3-27 | keep | `execute<-procedure` | 2.20 | 2.48 | -0.28 |
| at-33 | trap | `expensive<-adds` | 2.44 | 2.66 | -0.23 |
| d4-29 | keep | `lifespan<-no` | 1.47 | 1.68 | -0.21 |
| at-25 | trap | `weight<-utc` | 6.66 | 6.84 | -0.18 |
| at-12 | trap | `flavour<-other` | 2.49 | 2.66 | -0.17 |
| at-22 | trap | `flavour<-two` | 3.30 | 3.47 | -0.16 |
| d2-17 | keep | `plan<-schedule` | 3.82 | 3.97 | -0.15 |
| d4-42 | keep | `diagnostics<-debug` | 7.00 | 7.12 | -0.13 |
| d3-10 | keep | `quota<-remaining` | 2.78 | 2.89 | -0.11 |
| d4-27 | keep | `perform<-procedure` | 2.38 | 2.48 | -0.10 |
| d5-18 | keep | `gap<-freeze` | 5.26 | 5.23 | +0.04 |
| d3-09 | keep | `unused<-page` | 3.52 | 3.47 | +0.05 |
| d5-02 | keep | `existing<-starting` | 0.35 | 0.29 | +0.07 |
| d3-29 | keep | `reliability<-availability` | 2.51 | 2.44 | +0.08 |
| d3-19 | keep | `modification<-change` | 5.15 | 4.98 | +0.17 |
| d3-42 | keep | `management<-admin` | 7.28 | 7.08 | +0.20 |
| d3-30 | keep | `threshold<-percent` | 1.53 | 1.34 | +0.20 |
| d2-06 | keep | `margin<-budget` | 3.10 | 2.89 | +0.21 |
| d4-43 | keep | `identification<-only` | 7.26 | 7.00 | +0.26 |
| d3-02 | keep | `today<-only` | 0.67 | 0.29 | +0.39 |
| d3-28 | keep | `validity<-identity` | 1.72 | 1.30 | +0.43 |
| d2-25 | keep | `benchmark<-percent` | 1.82 | 1.34 | +0.49 |
| d2-15 | keep | `repair<-emergency` | 5.25 | 4.76 | +0.49 |
| d2-09 | keep | `manual<-flag` | 2.59 | 2.07 | +0.52 |
| d2-39 | keep | `administrator<-admin` | 7.68 | 7.08 | +0.60 |
| d3-11 | keep | `fix<-confirm` | 2.55 | 1.91 | +0.64 |
| d5-31 | keep | `maintain<-snapshot` | 1.60 | 0.94 | +0.65 |
| d3-23 | keep | `renewal<-rotation` | 5.01 | 4.36 | +0.66 |
| d3-21 | keep | `pause<-start` | 4.11 | 3.43 | +0.67 |
| d2-14 | keep | `span<-freeze` | 5.90 | 5.23 | +0.68 |
| d2-02 | keep | `ongoing<-incident` | 0.98 | 0.29 | +0.70 |
| d3-43 | keep | `passkey<-credential` | 4.73 | 4.03 | +0.70 |
| d2-16 | keep | `halt<-freeze` | 4.19 | 3.43 | +0.76 |
| d2-24 | keep | `expiry<-minute` | 2.06 | 1.30 | +0.76 |
| d2-23 | keep | `lifetime<-refresh` | 2.08 | 1.30 | +0.78 |
| g48-synonym | keep | `secret<-vault` | 5.75 | 4.96 | +0.80 |
| d3-18 | keep | `opening<-window` | 6.05 | 5.23 | +0.82 |
| d4-21 | keep | `launch<-start` | 4.10 | 3.24 | +0.86 |
| d3-05 | keep | `standby<-secondary` | 0.90 | -0.03 | +0.94 |
| g39-synonym | keep | `route<-path` | 3.98 | 3.01 | +0.96 |
| g35-synonym | keep | `location<-path` | 5.18 | 4.20 | +0.98 |
| d2-38 | keep | `destination<-ack` | 4.59 | 3.59 | +1.00 |
| d5-29 | keep | `login<-session` | 2.87 | 1.70 | +1.17 |
| d4-28 | keep | `ticket<-auth` | 3.33 | 2.04 | +1.29 |
| d3-25 | keep | `refresh<-rotation` | 6.01 | 4.58 | +1.43 |
| d3-31 | keep | `keep<-snapshot` | 2.38 | 0.94 | +1.44 |
| d4-10 | keep | `failures<-error` | 5.09 | 3.65 | +1.44 |

Every trap scores below its control median (max margin -0.16), so the real word adds nothing over an unrelated one. But 2 keep rows score at or below that too (d3-27, d4-29), 0 of them ANSWER rows. Their rescues are topical as well: the passage answers the question whatever the missing word is.

Still open at q = 0.50, percentile per rescue attempt (each supporting chunk, then the final evidence):

- at-22: [0.83, 0.27, 0.83] -> ANSWER via `flavour<-rolling`
- at-25: [0.12, 0.61, 0.61] -> ANSWER via `weight<-only`

One chunk below the bar is not enough: another chunk passes and the answer goes through it.
