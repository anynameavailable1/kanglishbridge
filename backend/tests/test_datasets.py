import io
import unittest

import pandas as pd

from app.data_tools import clean_for_split, load_dataset, split_dataframe, validate_dataframe

SAMPLE = "../datasets/sample/synthetic_demo.csv"


class DatasetTests(unittest.TestCase):
    def test_sample_is_valid(self):
        rep = validate_dataframe(load_dataset(SAMPLE))
        self.assertEqual(rep["invalid_row_count"], 0)
        self.assertTrue(all(rep["supported_tasks"].values()))

    def test_detects_problems(self):
        df = pd.DataFrame({"source_romanized": ["a b", "a b", "", "ನಾನು"], "source_kn": ["ಅ", "ಅ", "", "x"],
                           "target_en": ["x", "x", "", "ಕ"]})
        rep = validate_dataframe(df)
        self.assertEqual(rep["duplicate_rows"], 1)
        self.assertEqual(rep["empty_rows"], 1)
        self.assertGreaterEqual(rep["invalid_row_count"], 1)

    def test_classification_dataset_is_rejected_as_translation_data(self):
        rep = validate_dataframe(pd.DataFrame({"text": ["hi"], "label": ["pos"]}))
        self.assertFalse(any(rep["supported_tasks"].values()))
        self.assertTrue(rep["warnings"])

    def test_jsonl_loading(self):
        raw = '{"source_romanized":"a","source_kn":"ಅ","target_en":"a"}\n'.encode()
        self.assertEqual(len(load_dataset(raw, "jsonl")), 1)

    def test_split_is_reproducible_and_leak_free(self):
        df = load_dataset(SAMPLE)
        df = pd.concat([df, df.iloc[:3]])           # inject duplicates
        a = split_dataframe(df, seed=42)
        b = split_dataframe(df, seed=42)
        for x, y in zip(a, b):
            pd.testing.assert_frame_equal(x, y)
        sets = [set(p["source_romanized"].str.lower()) for p in a]
        self.assertFalse(sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2])
        self.assertEqual(sum(len(p) for p in a), len(clean_for_split(df)))


if __name__ == "__main__":
    unittest.main()
