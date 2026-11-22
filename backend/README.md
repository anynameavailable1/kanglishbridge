# Backend

Run from this folder (`kanglishbridge/backend`). Full instructions: `../README.md`.

    uvicorn app.main:app --host 127.0.0.1 --port 8000
    python -m unittest discover -s tests -t .      # or: pytest

Endpoints: `GET /health`, `POST /api/v1/translate`, `POST /api/v1/feedback`, `POST /api/v1/tokens/override`, `POST /api/v1/datasets/validate`.

To add another model, subclass `BaseTranslator` / `BaseTransliterator` in `app/nlp/base.py` and construct it in `build_default_pipeline()` (`app/nlp/pipeline.py`).
Tests use fakes from `tests/helpers.py` only; the production path never imports them.
