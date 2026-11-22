"""Central configuration. Every value can be overridden with a KB_* environment variable."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent


def _flag(name: str, default: bool) -> bool:
    return os.getenv(name, "1" if default else "0").strip().lower() in {"1", "true", "yes"}


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    max_text_chars: int
    request_timeout_s: float
    translator_model_id: str
    device: str                 # "auto" | "cpu" | "cuda"
    num_beams: int
    max_length: int
    translit_beam_width: int
    translit_rescore: bool
    protect_english: bool
    skip_model_load: bool       # only for tests / UI work without models
    cors_origin_regex: str
    max_upload_bytes: int
    data_dir: Path
    vocab_path: Path
    hints_path: Path
    overrides_path: Path
    feedback_path: Path
    extra_wordlist: Path | None


def load_settings() -> Settings:
    data_dir = Path(os.getenv("KB_DATA_DIR", BACKEND_DIR / "data"))
    extra = os.getenv("KB_EXTRA_ENGLISH_WORDLIST")
    ext_id = os.getenv("KB_EXTENSION_ID", "").strip()
    origin = rf"^chrome-extension://{ext_id}$" if ext_id else r"^chrome-extension://[a-p]{32}$"
    return Settings(
        host=os.getenv("KB_HOST", "127.0.0.1"),
        port=int(os.getenv("KB_PORT", "8000")),
        max_text_chars=int(os.getenv("KB_MAX_TEXT_CHARS", "5000")),
        request_timeout_s=float(os.getenv("KB_REQUEST_TIMEOUT_S", "120")),
        translator_model_id=os.getenv("KB_TRANSLATOR_MODEL", "ai4bharat/indictrans2-indic-en-dist-200M"),
        device=os.getenv("KB_DEVICE", "auto").lower(),
        num_beams=int(os.getenv("KB_NUM_BEAMS", "5")),
        max_length=int(os.getenv("KB_MAX_LENGTH", "256")),
        translit_beam_width=int(os.getenv("KB_TRANSLIT_BEAM", "10")),
        translit_rescore=_flag("KB_TRANSLIT_RESCORE", True),
        protect_english=_flag("KB_PROTECT_ENGLISH", True),
        skip_model_load=_flag("KB_SKIP_MODEL_LOAD", False),
        cors_origin_regex=origin,
        max_upload_bytes=int(os.getenv("KB_MAX_UPLOAD_BYTES", str(5 * 1024 * 1024))),
        data_dir=data_dir,
        vocab_path=data_dir / "english_vocab.txt",
        hints_path=data_dir / "kannada_hints.txt",
        overrides_path=data_dir / "token_overrides.json",
        feedback_path=data_dir / "feedback.jsonl",
        extra_wordlist=Path(extra) if extra else None,
    )
