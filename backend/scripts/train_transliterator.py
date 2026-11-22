"""Prepare word-pair data for OPTIONAL IndicXlit fine-tuning. This script does NOT train anything.

It aligns source_romanized with source_kn word-by-word (only for rows where both have the same number
of words), drops English-protected words, de-duplicates, and splits BY WORD so no word is in two splits.
Output: word_pairs_{train,val,test}.tsv (romanized<TAB>kannada) in --out.

Training itself must follow the official IndicXlit training documentation (fairseq based):
https://github.com/AI4Bharat/IndicXlit  -- consult it for the exact commands; none are invented here.
Only fine-tune with a large (thousands of pairs), human-verified, clean dataset.
"""
import argparse, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import load_settings  # noqa: E402
from app.data_tools import load_dataset  # noqa: E402
from app.nlp.pipeline import build_router  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("path"); ap.add_argument("--out", required=True); ap.add_argument("--seed", type=int, default=42)
a = ap.parse_args()
df = load_dataset(a.path)
router = build_router(load_settings())
pairs = {}
for _, r in df.iterrows():
    rom, kn = r["source_romanized"].split(), r["source_kn"].split()
    if len(rom) != len(kn):
        continue
    for w, k in zip(rom, kn):
        w = w.strip(".,!?;:").lower()
        if w.isalpha() and w not in router.english:
            pairs.setdefault(w, set()).add(k.strip(".,!?;:"))
words = sorted(pairs); random.Random(a.seed).shuffle(words)
n = len(words); cut1, cut2 = int(n * 0.8), int(n * 0.9)
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
for name, ws in (("train", words[:cut1]), ("val", words[cut1:cut2]), ("test", words[cut2:])):
    lines = [f"{w}\t{k}" for w in ws for k in sorted(pairs[w])]
    (out / f"word_pairs_{name}.tsv").write_text("\n".join(lines), encoding="utf-8")
    print(name, len(lines), "pairs")
if n < 2000:
    print("WARNING: fewer than 2,000 unique words; fine-tuning is unlikely to help and may hurt.")
