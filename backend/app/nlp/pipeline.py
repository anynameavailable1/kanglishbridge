"""End-to-end pipeline:  clean -> sentence split -> token routing -> IndicXlit -> IndicTrans2 -> output.

This file imports no model libraries and no web framework, so it is unit-testable with injected
fakes (tests only) while production wires in the real IndicXlit / IndicTrans2 adapters.
"""
from __future__ import annotations

import logging
import time

from .base import BaseTransliterator, BaseTranslator, InferenceError
from .language_detector import clean_whitespace, has_other_indic_script, split_sentences, tokenize
from .token_router import Label, RoutedToken, TokenRouter

logger = logging.getLogger(__name__)
_KANNADA_LABELS = {Label.ROMAN_KN, Label.KN_SCRIPT}


class TranslationPipeline:
    def __init__(self, router: TokenRouter, transliterator: BaseTransliterator, translator: BaseTranslator,
                 max_chars: int = 5000) -> None:
        self.router, self.transliterator, self.translator, self.max_chars = router, transliterator, translator, max_chars

    def process(self, text: str) -> dict:
        t0 = time.perf_counter()
        original = text
        text = clean_whitespace(text)
        if not text:
            raise ValueError("Text is empty")
        if len(text) > self.max_chars:
            raise ValueError(f"Text exceeds {self.max_chars} characters")

        warnings: list[str] = []
        if has_other_indic_script(text):
            warnings.append("Text in scripts other than Kannada is passed through unchanged.")

        sentences = split_sentences(text)
        routed_all: list[list[RoutedToken]] = []
        kn_sentences: list[str] = []
        translate_idx: list[int] = []
        labels_seen: set[Label] = set()

        t_translit = time.perf_counter()
        for idx, sent in enumerate(sentences):
            routed = self.router.route(tokenize(sent))
            routed_all.append(routed)
            labels_seen.update(r.label for r in routed)
            kn_sentences.append(self._to_kannada_script(routed, warnings))
            if any(r.label in _KANNADA_LABELS for r in routed):
                translate_idx.append(idx)
        translit_ms = (time.perf_counter() - t_translit) * 1000

        for r in (r for routed in routed_all for r in routed if r.warning):
            if r.warning not in warnings:
                warnings.append(r.warning)
        unsure = sorted({r.text for routed in routed_all for r in routed
                         if r.uncertain and r.label is Label.ROMAN_KN})
        if unsure:
            warnings.append("Unknown words were treated as Romanized Kannada: " + ", ".join(unsure[:8]))

        t_trans = time.perf_counter()
        translations = self.translator.translate([kn_sentences[i] for i in translate_idx]) if translate_idx else []
        trans_ms = (time.perf_counter() - t_trans) * 1000
        if len(translations) != len(translate_idx):
            raise InferenceError("Translator returned an unexpected number of sentences")
        by_idx = dict(zip(translate_idx, translations))

        if not translate_idx:
            warnings.append("No Kannada detected; the text was returned unchanged.")
        final = " ".join(by_idx.get(i, sentences[i]) for i in range(len(sentences)))

        languages = []
        if labels_seen & _KANNADA_LABELS:
            languages.append("Kannada")
        if labels_seen & {Label.ENGLISH, Label.PROPER}:
            languages.append("English")

        return {
            "original_text": original,
            "detected_languages": languages,
            "normalized_text": " ".join(kn_sentences),
            "translated_text": final,
            "warnings": warnings,
            "tokens": [{"text": r.text, "label": r.label.value} for routed in routed_all for r in routed
                       if r.label not in (Label.SPACE, Label.SYMBOL)],
            "latency_ms": {"transliteration": round(translit_ms, 1), "translation": round(trans_ms, 1),
                           "total": round((time.perf_counter() - t0) * 1000, 1)},
        }

    def _to_kannada_script(self, routed: list[RoutedToken], warnings: list[str]) -> str:
        parts = []
        for r in routed:
            if r.label is Label.ROMAN_KN:
                try:
                    parts.append(self.transliterator.transliterate_word(r.text))
                except InferenceError:
                    logger.exception("Transliteration failed for a token")
                    msg = f"Could not transliterate '{r.text}'; kept as written."
                    if msg not in warnings:
                        warnings.append(msg)
                    parts.append(r.text)
            else:
                parts.append(r.text)
        return "".join(parts)


def build_default_pipeline(settings, router: TokenRouter | None = None) -> TranslationPipeline:
    """Loads the REAL pretrained models. Raises ModelLoadError if either cannot be loaded."""
    from .transliterator import IndicXlitTransliterator
    from .translator import IndicTrans2Translator

    router = router or build_router(settings)
    xlit = IndicXlitTransliterator(settings.translit_beam_width, settings.translit_rescore)
    xlit.load()
    mt = IndicTrans2Translator(settings.translator_model_id, settings.device, settings.num_beams, settings.max_length)
    mt.load()
    return TranslationPipeline(router, xlit, mt, settings.max_text_chars)


def build_router(settings, protect_english: bool | None = None) -> TokenRouter:
    return TokenRouter(settings.vocab_path, settings.hints_path, settings.overrides_path, settings.extra_wordlist,
                       settings.protect_english if protect_english is None else protect_english)
