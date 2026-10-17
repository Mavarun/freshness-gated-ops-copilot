"""WordNet data.noun / index.noun parsing and the corpus neighbour table builder."""

from ops_copilot.wordnet_senses import (
    build_neighbour_table,
    iter_relations,
    parse_data_noun,
    parse_index_noun,
)

# Synthetic WordNet-format lines (offsets/lex ids invented for the test).
DATA = [
    "  1 This software and database is being provided ... (license header)\n",
    "00000001 03 n 01 genus 0 000 | the parent\n",
    "00000002 03 n 02 alpha 0 alias 0 001 @ 00000001 n 0000 | first child\n",
    "00000003 03 n 01 beta 0 001 @ 00000001 n 0000 | second child\n",
    "00000004 03 n 01 gamma 0 001 @ 00000002 n 0000 | grandchild\n",
    "00000005 03 n 01 omega 0 001 @i 00000001 n 0000 | instance child\n",
]
INDEX = [
    "  1 license header\n",
    "alpha n 1 1 @ 1 0 00000002\n",
    "beta n 1 1 @ 1 0 00000003\n",
    "genus n 1 1 ~ 1 0 00000001\n",
    "gamma n 1 1 @ 1 0 00000004\n",
    "omega n 1 1 @i 1 0 00000005\n",
    "alias n 1 1 @ 1 0 00000002\n",
    "x_y n 1 0 1 0 00000003\n",
]


def test_parse_data_noun_reads_lemmas_and_hypernyms():
    syn = parse_data_noun(DATA)
    assert set(syn) == {"00000001", "00000002", "00000003", "00000004", "00000005"}
    assert syn["00000002"].lemmas == ("alpha", "alias")
    assert syn["00000002"].hypernyms == ("00000001",)
    # instance hypernyms (@i) count as hypernyms
    assert syn["00000005"].hypernyms == ("00000001",)
    assert syn["00000001"].gloss == "the parent"


def test_parse_index_noun_keeps_sense_order():
    idx = parse_index_noun(INDEX)
    assert idx["alpha"] == ("00000002",)
    assert idx["x_y"] == ("00000003",)


def test_relations_cover_syn_hyper_hypo_and_sibling_with_fanout():
    rels = set(iter_relations(parse_data_noun(DATA), parse_index_noun(INDEX)))
    assert ("alpha", "alias", "syn", 0, 0) in rels
    assert ("alpha", "genus", "hyper", 0, 0) in rels
    assert ("alpha", "gamma", "hypo", 0, 0) in rels
    # genus has three hyponyms (alpha/alias, beta, omega): fan-out 3
    assert ("alpha", "beta", "sib", 3, 0) in rels
    assert ("beta", "omega", "sib", 3, 0) in rels
    # multi-word lemmas are never keys
    assert not any(r[0] == "x_y" for r in rels)


def test_table_keeps_only_corpus_targets_and_best_relation():
    table = build_neighbour_table(
        parse_data_noun(DATA), parse_index_noun(INDEX), ["genus", "beta", "unrelated"]
    )
    assert table["alpha"] == [["genus", "hyper", 1, 0, 0], ["beta", "sib", 2, 3, 0]]
    assert "unrelated" not in {r[0] for rows in table.values() for r in rows}
    # a word is never its own neighbour
    assert all(r[0] != k for k, rows in table.items() for r in rows)
