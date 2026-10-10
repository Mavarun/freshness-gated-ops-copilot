# Stack Exchange data: attribution and licence (ops-domain word vectors)

`se_ppmi_svd.json.gz` holds 6,000 lowercase words and one 48-dimensional
int8 vector per word: positive-PMI word co-occurrence statistics, reduced by
truncated SVD, computed from questions and answers posted on Stack Exchange.
It contains **no post text, titles, user names or post ids**. The raw API
pages it was built from are not in this repository; they are the same
snapshot as the QA translation table (`data/qa/`), pinned by the same
SHA-256 in `meta.raw_sha256`, and `scripts/build_domain_vectors.py` refuses
any other snapshot.

- **Source:** Stack Exchange API v2.3, `/questions` with answers
  (<https://api.stackexchange.com/2.3/questions>), most-voted and most recently
  active questions, fetched 2026-10-08 by `scripts/fetch_stackexchange_qa.py`.
  Only train-split questions were used (`qa_translation.is_test` false).
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
  links do not apply.
- **Input licences:** user contributions are licensed CC BY-SA 2.5, 3.0 or 4.0
  depending on the post date (<https://stackoverflow.com/help/licensing>).
- **Licence of this file:** shared under the inputs' terms,
  **CC BY-SA 4.0** (<https://creativecommons.org/licenses/by-sa/4.0/>), with
  the attribution above. It was changed (tokenised, counted, PMI-weighted,
  reduced by SVD and quantised to int8). The repository's MIT licence covers
  the code only, not this file.
