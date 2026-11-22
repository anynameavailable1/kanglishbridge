"""Usage: python scripts/validate_dataset.py ../datasets/sample/synthetic_demo.csv"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.data_tools import load_dataset, validate_dataframe  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("path")
args = ap.parse_args()
report = validate_dataframe(load_dataset(args.path))
print(json.dumps(report, indent=2, ensure_ascii=False))
sys.exit(1 if report["invalid_row_count"] or report["expected_columns_missing"] == list(
    ["source_romanized", "source_kn", "target_en"]) else 0)
