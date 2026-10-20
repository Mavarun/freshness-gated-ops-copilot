# Datamuse means-like snapshot

`ml_neighbours.json.gz` is derived from the [Datamuse API](https://www.datamuse.com/api/)
`/words?ml=<word>&max=100&md=p` ("means like") responses, fetched on 2026-10-20 for
the 440 plain content words of `data/corpus` and nothing else (no eval word was
queried). Per the Datamuse documentation, single-word `ml` results draw on WordNet 3.0,
dictionaries crawled by OneLook, the PPDB "XXL" lexical paraphrases and word2vec.

Acknowledgement, as the Datamuse API asks of public projects: word data from the
Datamuse API (datamuse.com). The raw responses are not committed; the table keeps only,
per result word, the corpus words whose list it appeared in, its 1-based rank there,
the Datamuse noun tag and the direction. `meta.raw_sha256` pins the canonical raw
responses and `meta.fetched_on` the fetch date; the live API can change, so a rebuild
on another day may differ.

Rebuild:

    python scripts/fetch_datamuse_ml.py --raw-dir /tmp/datamuse_raw
    python scripts/build_datamuse_neighbours.py --raw-dir /tmp/datamuse_raw --fetched-on 2026-10-20
