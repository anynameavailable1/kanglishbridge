"""Clean, de-duplicate and split a dataset (fixed seed) into train/val/test CSVs.

Usage: python scripts/prepare_dataset.py ../datasets/sample/synthetic_demo.csv --out ../datasets/sample/splits
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.data_tools import load_dataset, split_dataframe, validate_dataframe  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("path")
ap.add_argument("--out", required=True)
ap.add_argument("--seed", type=int, default=42)
ap.add_argument("--val", type=float, default=0.1)
ap.add_argument("--test", type=float, default=0.1)
a = ap.parse_args()

df = load_dataset(a.path)
rep = validate_dataframe(df)
if rep["invalid_row_count"]:
    print(f"WARNING: {rep['invalid_row_count']} invalid rows will be kept unless you fix them; run validate_dataset.py")
train, val, test = split_dataframe(df, a.seed, a.val, a.test)
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
for name, part in (("train", train), ("val", val), ("test", test)):
    part.to_csv(out / f"{name}.csv", index=False, encoding="utf-8")
    print(f"{name}: {len(part)} rows -> {out / (name + '.csv')}")
print(f"seed={a.seed}; rows sharing a source sentence were removed so no sentence appears in two splits.")
