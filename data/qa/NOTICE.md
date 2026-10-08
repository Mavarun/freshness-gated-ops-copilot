# Stack Exchange data: attribution and licence

`se_qa_translation.json.gz` is a table of word statistics (IBM Model 1
translation probabilities and shrunk lifts between question-title words and
answer words) derived from questions and answers posted on Stack Exchange.
It contains **no post text, titles, user names or post ids**: each entry is a
lowercase content word and three numbers. The raw API pages it was built from
are not in this repository (they are pinned by SHA-256 in the table's `meta`).

- **Source:** Stack Exchange API v2.3, `/questions` with answers
  (<https://api.stackexchange.com/2.3/questions>), most-voted and most recently
  active questions, fetched 2026-10-08 by `scripts/fetch_stackexchange_qa.py`.
- **Attribution:** questions and answers by the users of
  [Server Fault](https://serverfault.com),
  [Super User](https://superuser.com),
  [Unix & Linux](https://unix.stackexchange.com),
  [Ask Ubuntu](https://askubuntu.com),
  [Database Administrators](https://dba.stackexchange.com),
  [Information Security](https://security.stackexchange.com),
  [DevOps](https://devops.stackexchange.com) and
  [Network Engineering](https://networkengineering.stackexchange.com);
  Stack Exchange Inc. Individual posts are not reproduced, so per-post author
  links do not apply; the per-site pair counts are in `meta.sites`.
- **Input licences:** user contributions are licensed CC BY-SA 2.5, 3.0 or 4.0
  depending on the post date (<https://stackoverflow.com/help/licensing>). The
  answer counts per licence are in `meta.licenses`
  (2.5: 2,089; 3.0: 17,203; 4.0: 16,818).
- **Licence of this table:** to be safe it is shared under the inputs' terms,
  **CC BY-SA 4.0** (<https://creativecommons.org/licenses/by-sa/4.0/>), with
  the attribution above. It was changed (tokenised, aligned by EM, reduced to
  lifts >= 1.0 for the corpus vocabulary). The repository's MIT licence covers
  the code only, not this file.
