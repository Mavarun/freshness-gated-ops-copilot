# EFF large diceware wordlist

`eff_large_wordlist.txt.gz` is the EFF "large" wordlist for passphrases (7,776 words,
five dice per word), published by the Electronic Frontier Foundation at
https://www.eff.org/files/2016/07/18/eff_large_wordlist.txt and described in
"EFF's New Wordlists for Random Passphrases" (Joseph Bonneau, 2016,
https://www.eff.org/deeplinks/2016/07/new-wordlists-random-passphrases).
It was downloaded on 2026-10-29 and is committed unchanged (zero-mtime gzip of the
raw file, sha256 `addd35536511597a02fa0a9ff1e5284677b8883b83e986e43f15a3db996b903e`).

Licence: EFF publishes its site content under the Creative Commons Attribution 3.0
United States licence (CC BY 3.0 US, https://creativecommons.org/licenses/by/3.0/us/,
see https://www.eff.org/copyright). Attribution: wordlist by the Electronic Frontier
Foundation. The repository's MIT licence covers the code only, not this file.

Use here: the list is the word source of the *real-wordlist* passphrase probe
(`ops_copilot.passphrase_wordlist`). Until Oct 29 it was never read by the detector.
Since Oct 30 the detector's list-membership arm (`passphrase.generator_words`,
`wordlist_compounds="all4"`, `wordlist_space=True`) reads it too, because real
generators (Bitwarden's `EFFLongWordList`, for one) draw from it. The probe and the arm
therefore share the list, so probe recall overstates real-world recall. The off-list
control (`passphrase_wordlist.offlist_words`, WordNet nouns not on the list) measures
that gap.
