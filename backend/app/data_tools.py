"""Dataset loading, validation, de-duplication and leak-free splitting (CSV / JSONL).

Column meaning
  source_romanized : the Kanglish text as people type it
  source_kn        : the same sentence in Kannada script (human-verified)
  target_en        : natural English reference translation
Tasks:  source_romanized+target_en -> end-to-end evaluation
        source_romanized+source_kn -> transliteration training / evaluation
        source_kn+target_en        -> machine-translation training / evaluation
"""
from __future__ import annotations

import io
import re
from pathlib import Path

import pandas as pd

COLUMNS = ["source_romanized", "source_kn", "target_en"]
_KN = re.compile(r"[\u0C80-\u0CFF]")
TASKS = {
    "end_to_end_evaluation": ["source_romanized", "target_en"],
    "transliteration": ["source_romanized", "source_kn"],
    "machine_translation": ["source_kn", "target_en"],
}


def load_dataset(source, fmt: str | None = None) -> pd.DataFrame:
    """source: path or bytes. fmt: 'csv' | 'jsonl' (inferred from the path suffix if omitted)."""
    if fmt is None:
        fmt = Path(source).suffix.lstrip(".").lower()
    buf = io.BytesIO(source) if isinstance(source, (bytes, bytearray)) else source
    if fmt == "csv":
        return pd.read_csv(buf, dtype=str, keep_default_na=False, encoding="utf-8")
    if fmt in ("jsonl", "json"):
        return pd.read_json(buf, lines=True, dtype=str)
    raise ValueError("Unsupported format; use .csv or .jsonl")


def _blank(x):
    if isinstance(x, pd.DataFrame):
        return x.apply(_blank)
    return x.isna() | (x.astype(str).str.strip() == "")


def validate_dataframe(df: pd.DataFrame) -> dict:
    present = [c for c in COLUMNS if c in df.columns]
    report: dict = {
        "rows": int(len(df)), "columns": list(map(str, df.columns)),
        "expected_columns_present": present,
        "expected_columns_missing": [c for c in COLUMNS if c not in df.columns],
        "missing_values": {c: int(df[c].isna().sum()) for c in df.columns},
        "empty_values": {c: int(_blank(df[c]).sum()) for c in present},
        "warnings": [],
    }
    if {"text", "label"} <= set(df.columns) and not present:
        report["warnings"].append("Columns look like a text/label classification dataset, not a translation "
                                  "dataset; it cannot be used here.")
    report["empty_rows"] = int(_blank(df[present]).all(axis=1).sum()) if present else 0

    dup_cols = present or list(df.columns)
    report["duplicate_rows"] = int(df.duplicated(subset=dup_cols).sum())
    conflicts = 0
    if "target_en" in present and len(present) > 1:
        src = [c for c in present if c != "target_en"]
        conflicts = int((df.drop_duplicates(subset=present).duplicated(subset=src, keep=False)).sum())
    report["conflicting_duplicates"] = conflicts

    invalid = []
    for i, row in df.iterrows():
        reasons = []
        if "source_kn" in present and row["source_kn"].strip() and not _KN.search(row["source_kn"]):
            reasons.append("source_kn has no Kannada characters")
        if "source_romanized" in present and _KN.search(row["source_romanized"]):
            reasons.append("source_romanized contains Kannada script")
        if "target_en" in present and _KN.search(row["target_en"]):
            reasons.append("target_en contains Kannada script")
        if reasons:
            invalid.append({"row_index": int(i), "reasons": reasons})
    report["invalid_row_count"] = len(invalid)
    report["invalid_rows"] = invalid[:50]

    report["statistics"] = {
        c: {"mean_chars": round(float(df[c].astype(str).str.len().mean()), 1) if len(df) else 0.0,
            "mean_words": round(float(df[c].astype(str).str.split().str.len().mean()), 1) if len(df) else 0.0}
        for c in present}
    report["supported_tasks"] = {
        t: all(c in present and not _blank(df[c]).all() for c in cols) for t, cols in TASKS.items()}
    if len(df) < 1000:
        report["warnings"].append("Fewer than 1,000 rows: fine for evaluation, too small for fine-tuning.")
    return report


def clean_for_split(df: pd.DataFrame) -> pd.DataFrame:
    """Drop empty-required rows and rows sharing a source (prevents train/test leakage)."""
    cols = [c for c in COLUMNS if c in df.columns]
    df = df[~_blank(df[cols]).any(axis=1)].copy()
    key = df[[c for c in ("source_romanized", "source_kn") if c in df.columns]].apply(
        lambda s: s.str.lower().str.replace(r"\s+", " ", regex=True).str.strip())
    return df.loc[~key.duplicated()].reset_index(drop=True)


def split_dataframe(df: pd.DataFrame, seed: int = 42, val: float = 0.1, test: float = 0.1):
    from sklearn.model_selection import train_test_split
    df = clean_for_split(df)
    if len(df) < 10:
        raise ValueError("Need at least 10 clean rows to split")
    train_val, test_df = train_test_split(df, test_size=test, random_state=seed, shuffle=True)
    train_df, val_df = train_test_split(train_val, test_size=val / (1 - test), random_state=seed, shuffle=True)
    return train_df.reset_index(drop=True), val_df.reset_index(drop=True), test_df.reset_index(drop=True)
