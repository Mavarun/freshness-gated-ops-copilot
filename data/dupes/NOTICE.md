# Stack Exchange data: attribution and licence

`se_duplicate_paraphrase.json.gz` is a table of word statistics derived from the titles
of questions closed as duplicates on Stack Exchange and the titles of their originals
(per word: its strongest cross-pair partners with a G² score, a cross-pair count and a
same-title count). It contains **no post text, titles, user names or post ids**: each
entry is a lowercase content word and numbers. The archives it was built from are not
in this repository (they are pinned by SHA-256 in the table's `meta.archives_sha256`).

- **Source:** the Stack Exchange data dump of 2024-04
  (<https://archive.org/details/stackexchange>), `PostLinks.xml` rows with
  `LinkTypeId=3` (closed as duplicate) and the question titles of `Posts.xml`,
  read by `scripts/build_dupe_paraphrase.py`.
- **Attribution:** questions by the users of
  [Server Fault](https://serverfault.com),
  [Super User](https://superuser.com),
  [Unix & Linux](https://unix.stackexchange.com),
  [Ask Ubuntu](https://askubuntu.com),
  [Database Administrators](https://dba.stackexchange.com),
  [Information Security](https://security.stackexchange.com),
  [DevOps](https://devops.stackexchange.com) and
  [Network Engineering](https://networkengineering.stackexchange.com);
  Stack Exchange Inc. Individual posts are not reproduced, so per-post author links do
  not apply; the per-site pair counts are in `meta.sites`.
- **Input licence:** the data dump is licensed CC BY-SA 4.0
  (<https://creativecommons.org/licenses/by-sa/4.0/>).
- **Licence of this table:** shared under the same terms, **CC BY-SA 4.0**, with the
  attribution above. It was changed (tokenised, reduced to one-side-only word pairs,
  scored with G², cut to 40 partners per word).
