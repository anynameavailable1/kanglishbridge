"""Adapter interfaces. Implement these to plug in a newer transliteration/translation model."""
from __future__ import annotations

from abc import ABC, abstractmethod


class ModelLoadError(RuntimeError):
    """A model or its dependency could not be loaded."""


class InferenceError(RuntimeError):
    """A loaded model failed while processing input."""


class BaseTransliterator(ABC):
    """Romanized Kannada word -> Kannada script."""
    name = "base"

    @abstractmethod
    def load(self) -> None: ...

    @abstractmethod
    def transliterate_word(self, word: str) -> str: ...

    def candidates(self, word: str, k: int = 5) -> list[str]:
        return [self.transliterate_word(word)]


class BaseTranslator(ABC):
    """Kannada-script (possibly with Latin words) sentences -> English sentences."""
    name = "base"
    device = "cpu"

    @abstractmethod
    def load(self) -> None: ...

    @abstractmethod
    def translate(self, sentences: list[str]) -> list[str]: ...
