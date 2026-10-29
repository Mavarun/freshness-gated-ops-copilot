# Cued-passphrase detector: false positives on outside Stack Exchange text

Sentences with a credential noun followed by a word run, from public question titles and answers (none is a real secret, so every flag is a false positive). Neither split is blind: one earlier look at the test split (7 of 269 flagged, first 2,000 characters of each answer) prompted adding `text.STOPWORDS` to the stop list; the train split was only scanned after that change.

| split | candidate sentences | flagged | rate |
| --- | ---: | ---: | ---: |
| train | 3,020 | 28 | 0.009 |
| test | 306 | 0 | 0.000 |

Flagged spans on the test split (the words that would be redacted):

