import unittest

from app.nlp.language_detector import clean_whitespace, split_sentences, tokenize
from app.nlp.token_router import Label
from tests.helpers import make_pipeline


class TokenizerTests(unittest.TestCase):
    def test_lossless(self):
        for t in ["Naanu ivattu college ge baralla, swalpa work ide 😊", "ನಾನು 12/03/2025 ಬರ್ತೀನಿ!!", "a  b\nc"]:
            self.assertEqual("".join(x.text for x in tokenize(t)), t)

    def test_whitespace_cleaning_keeps_content(self):
        self.assertEqual(clean_whitespace("  hi   there \n\n  ok 😊 "), "hi there\n\nok 😊")

    def test_sentence_split(self):
        self.assertEqual(len(split_sentences("Naanu barthini. Neevu yaavaga? Sari!\nOk")), 4)
        self.assertEqual(split_sentences("Price is 3.5 rupees"), ["Price is 3.5 rupees"])


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.pipe, self.xlit, self.mt = make_pipeline()

    def labels(self, text):
        return {t["text"]: t["label"] for t in self.pipe.process(text)["tokens"]}

    def test_mixed_sentence_routes_english_and_kannada(self):
        lab = self.labels("Naanu ivattu college ge baralla, swalpa work ide.")
        self.assertEqual(lab["college"], Label.ENGLISH.value)
        self.assertEqual(lab["work"], Label.ENGLISH.value)
        self.assertEqual(lab["Naanu"], Label.ROMAN_KN.value)
        self.assertEqual(lab["baralla"], Label.ROMAN_KN.value)

    def test_english_words_never_transliterated(self):
        self.pipe.process("Nale meeting ide, please send the OTP")
        for w in ("meeting", "please", "send", "the", "OTP"):
            self.assertNotIn(w, self.xlit.calls)

    def test_technical_terms_preserved(self):
        self.pipe.process("Backend server deploy madbeku")
        self.assertEqual(self.xlit.calls, ["madbeku"])

    def test_proper_noun_mid_sentence_preserved(self):
        self.pipe.process("Nanna friend Ravi bandidane")
        self.assertNotIn("Ravi", self.xlit.calls)

    def test_manual_override_wins(self):
        self.pipe.router.overrides["baralla"] = "english"
        self.pipe.process("Naanu baralla")
        self.assertNotIn("baralla", self.xlit.calls)

    def test_ambiguous_unknown_word_is_flagged(self):
        r = self.pipe.process("Naanu zzyzx barthini")
        self.assertTrue(any("zzyzx" in w for w in r["warnings"]))

    def test_protection_off_transliterates_english(self):
        pipe, xlit, _ = make_pipeline(protect_english=False)
        pipe.process("Nale meeting ide")
        self.assertIn("meeting", xlit.calls)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.pipe, self.xlit, self.mt = make_pipeline()

    def test_empty_input_rejected(self):
        for bad in ["", "   ", "\n\t"]:
            with self.assertRaises(ValueError):
                self.pipe.process(bad)

    def test_english_only_is_returned_unchanged_with_warning(self):
        r = self.pipe.process("Please send the report today.")
        self.assertEqual(r["translated_text"], "Please send the report today.")
        self.assertEqual(r["detected_languages"], ["English"])
        self.assertEqual(self.mt.received, [])
        self.assertTrue(r["warnings"])

    def test_native_kannada_goes_straight_to_translator(self):
        r = self.pipe.process("ನಾನು ಮನೆಗೆ ಹೋಗುತ್ತಿದ್ದೇನೆ")
        self.assertEqual(self.mt.received, [["ನಾನು ಮನೆಗೆ ಹೋಗುತ್ತಿದ್ದೇನೆ"]])
        self.assertEqual(self.xlit.calls, [])
        self.assertIn("Kannada", r["detected_languages"])

    def test_multiple_sentences_translated_as_sentences(self):
        r = self.pipe.process("Naanu barthini. Neevu yaavaga barthira?")
        self.assertEqual(len(self.mt.received[0]), 2)
        self.assertEqual(r["translated_text"].count("EN("), 2)

    def test_punctuation_numbers_emoji_survive_normalisation(self):
        r = self.pipe.process("Naanu 5 gante ge barthini 😊!!")
        for piece in ("5", "😊", "!!"):
            self.assertIn(piece, r["normalized_text"])

    def test_dates_survive(self):
        self.assertIn("12/03/2025", self.pipe.process("Exam 12/03/2025 ide")["normalized_text"])

    def test_long_input(self):
        text = " ".join(["Naanu college ge hogthini."] * 150)
        r = self.pipe.process(text)
        self.assertEqual(len(self.mt.received[0]), 150)
        self.assertTrue(r["translated_text"])

    def test_too_long_rejected(self):
        with self.assertRaises(ValueError):
            self.pipe.process("a" * (self.pipe.max_chars + 1))

    def test_spelling_variants_all_reach_translator(self):
        for v in ["Naanu college ge baralla", "Nanu college ge baralla", "Naanu college ge baraalla"]:
            self.pipe.process(v)
        self.assertEqual(len(self.mt.received), 3)

    def test_transliteration_failure_is_reported_not_swallowed(self):
        pipe, _, _ = make_pipeline(fail_on={"baralla"})
        r = pipe.process("Naanu baralla")
        self.assertTrue(any("baralla" in w for w in r["warnings"]))

    def test_translator_failure_propagates(self):
        from app.nlp.base import InferenceError
        self.mt.translate = lambda s: (_ for _ in ()).throw(InferenceError("x"))
        with self.assertRaises(InferenceError):
            self.pipe.process("Naanu barthini")


if __name__ == "__main__":
    unittest.main()
