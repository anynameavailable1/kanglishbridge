"""AI4Bharat IndicXlit wrapper: Romanized Kannada -> Kannada script.

Uses the official `ai4bharat-transliteration` package (https://github.com/AI4Bharat/IndicXlit).
There is deliberately NO rule-based fallback: if the package/model cannot load, loading fails loudly.
"""
from __future__ import annotations

import logging
import threading

from .base import BaseTransliterator, InferenceError, ModelLoadError

logger = logging.getLogger(__name__)


class IndicXlitTransliterator(BaseTransliterator):
    name = "ai4bharat-indicxlit"

    def __init__(self, beam_width: int = 10, rescore: bool = True) -> None:
        self.beam_width = beam_width
        self.rescore = rescore
        self._engine = None
        self._cache: dict[str, list[str]] = {}
        self._lock = threading.Lock()

    def load(self) -> None:
        try:
            from ai4bharat.transliteration import XlitEngine
        except ImportError as exc:
            raise ModelLoadError(
                "ai4bharat-transliteration is not installed (it needs fairseq; see README, WSL2 section)") from exc
        try:
            self._engine = XlitEngine("kn", beam_width=self.beam_width, rescore=self.rescore, src_script_type="en")
        except Exception as exc:  # library raises assorted errors on download/model problems
            logger.exception("IndicXlit failed to initialise")
            raise ModelLoadError("IndicXlit failed to initialise") from exc
        logger.info("IndicXlit (kn) loaded")

    def candidates(self, word: str, k: int = 5) -> list[str]:
        if self._engine is None:
            raise InferenceError("IndicXlit is not loaded")
        key = f"{word.lower()}|{k}"
        if key in self._cache:
            return self._cache[key]
        try:
            with self._lock:  # the engine is not documented as thread-safe
                out = self._engine.translit_word(word.lower(), topk=k)
        except Exception as exc:
            raise InferenceError(f"IndicXlit failed on '{word}'") from exc
        cands = out.get("kn", []) if isinstance(out, dict) else list(out)
        if not cands:
            raise InferenceError(f"IndicXlit returned no candidates for '{word}'")
        self._cache[key] = cands
        return cands

    def transliterate_word(self, word: str) -> str:
        return self.candidates(word, k=1)[0]
