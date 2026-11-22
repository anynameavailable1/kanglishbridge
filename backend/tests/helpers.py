"""Fakes used ONLY by unit tests. Production code never imports this module."""
from app.config import load_settings
from app.nlp.base import BaseTransliterator, BaseTranslator, InferenceError
from app.nlp.pipeline import TranslationPipeline, build_router


class FakeTransliterator(BaseTransliterator):
    name = "fake"
    def __init__(self, fail_on=()): self.fail_on, self.calls = set(fail_on), []
    def load(self): pass
    def transliterate_word(self, word):
        self.calls.append(word)
        if word.lower() in self.fail_on:
            raise InferenceError("boom")
        return "ಕನ್" + word.lower()          # visibly 'Kannada-script' for assertions


class FakeTranslator(BaseTranslator):
    name = "fake"
    def __init__(self): self.received = []
    def load(self): pass
    def translate(self, sentences):
        self.received.append(list(sentences))
        return [f"EN({s})" for s in sentences]


def make_pipeline(fail_on=(), protect_english=True):
    s = load_settings()
    xlit, mt = FakeTransliterator(fail_on), FakeTranslator()
    return TranslationPipeline(build_router(s, protect_english), xlit, mt, s.max_text_chars), xlit, mt
