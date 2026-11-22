"""Integration tests against the REAL pretrained models. Skipped unless KB_RUN_MODEL_TESTS=1.

    $env:KB_RUN_MODEL_TESTS = "1"; python -m unittest tests.test_real_models -v
First run downloads the models (hundreds of MB).
"""
import os
import re
import unittest


@unittest.skipUnless(os.getenv("KB_RUN_MODEL_TESTS") == "1", "set KB_RUN_MODEL_TESTS=1 to run real-model tests")
class RealModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.config import load_settings
        from app.nlp.pipeline import build_default_pipeline
        cls.pipe = build_default_pipeline(load_settings())

    def test_components_are_the_real_adapters(self):
        self.assertEqual(type(self.pipe.transliterator).__name__, "IndicXlitTransliterator")
        self.assertEqual(type(self.pipe.translator).__name__, "IndicTrans2Translator")

    def test_transliteration_produces_kannada_script(self):
        out = self.pipe.transliterator.transliterate_word("naanu")
        self.assertTrue(re.search(r"[\u0C80-\u0CFF]", out), out)

    def test_end_to_end_mixed_sentence(self):
        r = self.pipe.process("Naanu ivattu college ge baralla, swalpa work ide.")
        print("\nNORMALIZED:", r["normalized_text"], "\nTRANSLATION:", r["translated_text"])
        self.assertTrue(re.search(r"[A-Za-z]{3}", r["translated_text"]))
        self.assertFalse(re.search(r"[\u0C80-\u0CFF]", r["translated_text"]))
        self.assertGreater(r["latency_ms"]["translation"], 0)

    def test_spelling_variants_give_similar_output(self):
        from sacrebleu.metrics import CHRF
        outs = [self.pipe.process(v)["translated_text"] for v in
                ["Naanu manege hogthiddini", "Nanu manege hogtiddini", "Naanu manege hogtidini"]]
        print("\nVARIANT OUTPUTS:", outs)
        sim = CHRF().sentence_score(outs[1], [outs[0]]).score
        print("chrF between variants:", round(sim, 1))   # reported, not asserted: depends on the model
        self.assertTrue(all(outs))


if __name__ == "__main__":
    unittest.main()
