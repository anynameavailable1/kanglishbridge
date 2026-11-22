# Known limitations (design-level; measure them with your own data)

These are expected failure modes of the approach. They have **not** been measured yet - run `scripts/evaluate.py` on real data and copy real examples from `results/error_analysis_worst15.csv` into this file.

1. **Transliteration:** IndicXlit has no context, so ambiguous spellings (short/informal words like "ge", "ke", heavy abbreviations, SMS spellings) can map to the wrong Kannada word; a wrong word then changes the translation.
2. **English detection:** routing is vocabulary-based. English words missing from `english_vocab.txt` get transliterated into Kannada letters; Kannada words that look English can be protected wrongly. Names at the start of a sentence are treated as ordinary words. Fix by editing the vocab/hints/overrides files.
3. **Translation:** IndicTrans2 is a Kannada->English model; mixed input (Latin words inside Kannada sentences) is outside its cleanest training distribution. It can drop, paraphrase or hallucinate content, change tense/negation (e.g. "baralla" = "won't come"), and handle slang poorly. Always check important messages.
4. **Evaluation:** BLEU/chrF with one reference under-scores valid paraphrases. English-token preservation is a rough string-match proxy. Small datasets give noisy numbers; the bundled sample is synthetic and unverified.
5. **WhatsApp:** depends on WhatsApp's page structure, which changes without notice; reading is selection-only by design.
6. **Fine-tuning:** not provided for IndicTrans2; the transliterator script only prepares data. Follow the official repositories for training.
