"""Evaluate the REAL pipeline on a held-out test CSV (needs source_romanized + target_en).

  python scripts/evaluate.py --test ../datasets/sample/splits/test.csv --out ../results/run1 [--ablation]
  python scripts/evaluate.py ... --make-human-template 30        # then fill adequacy/fluency (1-5)
  python scripts/evaluate.py ... --human-eval-file ../results/run1/human_eval_template.csv

Metrics: BLEU, chrF, chrF++, latency (mean/p50/p95), English-token preservation, optional human scores.
--ablation also runs with English protection OFF (everything transliterated) for a comparison table.
"""
import argparse, json, re, statistics, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import matplotlib; matplotlib.use("Agg")  # noqa: E702
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from sacrebleu.metrics import BLEU, CHRF  # noqa: E402

from app.config import load_settings  # noqa: E402
from app.data_tools import load_dataset  # noqa: E402
from app.nlp.pipeline import TranslationPipeline, build_default_pipeline, build_router  # noqa: E402
from app.nlp.token_router import Label  # noqa: E402
from app.nlp.language_detector import tokenize  # noqa: E402


def english_preservation(pipe, source: str, hyp: str):
    """Share of protected English source words (>=3 letters) that appear in the output. None if no such words."""
    words = [t.text.lower() for t in pipe.router.route(tokenize(source))
             if t.label is Label.ENGLISH and len(t.text) >= 3 and t.text.isalpha()]
    if not words:
        return None
    hyp_words = set(re.findall(r"[a-z']+", hyp.lower()))
    return sum(w in hyp_words for w in words) / len(words)


def run(pipe, df):
    rows = []
    for i, r in df.iterrows():
        t0 = time.perf_counter()
        res = pipe.process(r["source_romanized"])
        ms = (time.perf_counter() - t0) * 1000
        hyp = res["translated_text"]
        rows.append({"id": i, "source": r["source_romanized"], "normalized_kn": res["normalized_text"],
                     "reference": r["target_en"], "hypothesis": hyp, "latency_ms": round(ms, 1),
                     "chrf": round(CHRF().sentence_score(hyp, [r["target_en"]]).score, 1),
                     "english_preserved": english_preservation(pipe, r["source_romanized"], hyp),
                     "warnings": " | ".join(res["warnings"])})
    return pd.DataFrame(rows)


def summarise(res: pd.DataFrame) -> dict:
    hyps, refs = res["hypothesis"].tolist(), [res["reference"].tolist()]
    lat = sorted(res["latency_ms"])
    ep = res["english_preserved"].dropna()
    return {"n": len(res), "BLEU": round(BLEU().corpus_score(hyps, refs).score, 2),
            "chrF": round(CHRF().corpus_score(hyps, refs).score, 2),
            "chrF++": round(CHRF(word_order=2).corpus_score(hyps, refs).score, 2),
            "latency_mean_ms": round(statistics.mean(lat), 1), "latency_p50_ms": round(statistics.median(lat), 1),
            "latency_p95_ms": round(lat[min(len(lat) - 1, int(0.95 * len(lat)))], 1),
            "english_preservation": round(float(ep.mean()), 3) if len(ep) else None,
            "english_preservation_n": int(len(ep))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--ablation", action="store_true")
    ap.add_argument("--make-human-template", type=int, default=0)
    ap.add_argument("--human-eval-file")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    df = load_dataset(a.test)
    if not {"source_romanized", "target_en"} <= set(df.columns):
        sys.exit("Test file needs source_romanized and target_en columns")
    if "synthetic" in df.columns and df["synthetic"].astype(str).str.lower().eq("true").any():
        print("NOTE: this data is SYNTHETIC. Scores below are a tooling check, not real-world performance.")

    settings = load_settings()
    pipe = build_default_pipeline(settings)
    summaries = {"with_english_protection": None}
    res = run(pipe, df)
    res.to_csv(out / "results.csv", index=False, encoding="utf-8")
    summaries["with_english_protection"] = summarise(res)
    res.sort_values("chrf").head(15).to_csv(out / "error_analysis_worst15.csv", index=False, encoding="utf-8")

    if a.ablation:
        pipe2 = TranslationPipeline(build_router(settings, protect_english=False), pipe.transliterator,
                                    pipe.translator, settings.max_text_chars)
        res2 = run(pipe2, df); res2.to_csv(out / "results_no_protection.csv", index=False, encoding="utf-8")
        summaries["without_english_protection"] = summarise(res2)

    if a.make_human_template:
        t = res.sample(min(a.make_human_template, len(res)), random_state=42)[["id", "source", "hypothesis"]].copy()
        t["adequacy_1_5"] = ""; t["fluency_1_5"] = ""
        t.to_csv(out / "human_eval_template.csv", index=False, encoding="utf-8")
    if a.human_eval_file:
        h = pd.read_csv(a.human_eval_file).dropna(subset=["adequacy_1_5", "fluency_1_5"])
        if len(h):
            summaries["human_eval"] = {"n": len(h), "adequacy_mean": round(h["adequacy_1_5"].mean(), 2),
                                       "fluency_mean": round(h["fluency_1_5"].mean(), 2)}

    (out / "summary.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    table = pd.DataFrame(summaries).drop(columns=[c for c in ("human_eval",) if c in summaries])
    (out / "comparison.md").write_text(table.to_string(), encoding="utf-8")
    table.to_csv(out / "comparison.csv", encoding="utf-8")

    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    m = table.loc[["BLEU", "chrF", "chrF++"]].astype(float)
    m.plot.bar(ax=ax[0], rot=0, title="Translation quality"); ax[0].set_ylabel("score")
    ax[1].hist(res["latency_ms"], bins=15); ax[1].set_title("Latency per input (ms)"); ax[1].set_xlabel("ms")
    fig.tight_layout(); fig.savefig(out / "metrics.png", dpi=150)
    print(table.to_string()); print(f"\nSaved results to {out}")


if __name__ == "__main__":
    main()
