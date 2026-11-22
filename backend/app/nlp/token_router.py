"""Conservative routing of every token: English / Romanized Kannada / proper noun / etc.

Priority (first match wins):
  1. manual override   (data/token_overrides.json, editable through the API or by hand)
  2. ALL-CAPS acronym  (OTP, ATM)                                  -> english
  3. in BOTH vocab files (collision)                               -> english + warning
  4. in kannada_hints.txt                                          -> romanized_kannada
  5. in english_vocab.txt (+ optional system wordlist)             -> english
  6. Capitalised and not the first word of the sentence            -> proper_noun
  7. anything else                                                 -> romanized_kannada (flagged uncertain)

Honest limitation: this is a vocabulary heuristic, not a trained language-ID model. An English word
missing from the vocabulary will be sent to the transliterator. Extend data/english_vocab.txt to fix.
"""
from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .language_detector import Token, TokenKind

logger = logging.getLogger(__name__)
VALID_OVERRIDES = {"english", "romanized_kannada", "proper_noun"}


class Label(str, Enum):
    ROMAN_KN = "romanized_kannada"
    ENGLISH = "english"
    PROPER = "proper_noun"
    KN_SCRIPT = "kannada_script"
    NUMBER = "number"
    SPACE = "space"
    SYMBOL = "symbol"


@dataclass
class RoutedToken:
    text: str
    label: Label
    reason: str = ""
    uncertain: bool = False
    warning: str | None = None


def _read_words(path: Path | None) -> set[str]:
    if path is None or not Path(path).exists():
        return set()
    words: set[str] = set()
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0]
        words.update(w.lower() for w in line.split())
    return words


class TokenRouter:
    def __init__(self, vocab_path: Path, hints_path: Path, overrides_path: Path,
                 extra_wordlist: Path | None = None, protect_english: bool = True) -> None:
        self.protect_english = protect_english
        self.overrides_path = Path(overrides_path)
        self._lock = threading.Lock()
        self.english = _read_words(vocab_path) | _read_words(extra_wordlist)
        self.hints = _read_words(hints_path)
        self.overrides = self._load_overrides()

    def _load_overrides(self) -> dict[str, str]:
        if not self.overrides_path.exists():
            return {}
        try:
            data = json.loads(self.overrides_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.exception("token_overrides.json is not valid JSON; ignoring it")
            return {}
        return {k.lower(): v for k, v in data.items() if not k.startswith("_") and v in VALID_OVERRIDES}

    def set_override(self, word: str, label: str) -> None:
        if label not in VALID_OVERRIDES:
            raise ValueError(f"label must be one of {sorted(VALID_OVERRIDES)}")
        with self._lock:
            self.overrides[word.lower()] = label
            self.overrides_path.parent.mkdir(parents=True, exist_ok=True)
            self.overrides_path.write_text(
                json.dumps(self.overrides, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")

    def route(self, tokens: list[Token]) -> list[RoutedToken]:
        out: list[RoutedToken] = []
        seen_word = False
        for t in tokens:
            if t.kind is TokenKind.SPACE:
                out.append(RoutedToken(t.text, Label.SPACE))
            elif t.kind is TokenKind.SYMBOL:
                out.append(RoutedToken(t.text, Label.SYMBOL))
            elif t.kind is TokenKind.NUMBER:
                out.append(RoutedToken(t.text, Label.NUMBER))
            elif t.kind is TokenKind.KANNADA_SCRIPT:
                seen_word = True
                out.append(RoutedToken(t.text, Label.KN_SCRIPT))
            else:
                out.append(self._route_latin(t.text, first=not seen_word))
                seen_word = True
        return out

    def _route_latin(self, word: str, first: bool) -> RoutedToken:
        lw = word.lower().replace("\u2019", "'")
        if lw in self.overrides:
            return RoutedToken(word, Label(self.overrides[lw]), "manual override")
        if not self.protect_english:
            return RoutedToken(word, Label.ROMAN_KN, "english protection disabled")
        if word.isupper() and len(word) >= 2:
            return RoutedToken(word, Label.ENGLISH, "acronym")
        if lw in self.english and lw in self.hints:
            return RoutedToken(word, Label.ENGLISH, "collision", True,
                               f"'{word}' could be English or Romanized Kannada; treated as English "
                               f"(add an override if wrong).")
        if lw in self.hints:
            return RoutedToken(word, Label.ROMAN_KN, "known Kannada word")
        if lw in self.english or "'" in lw:
            return RoutedToken(word, Label.ENGLISH, "english vocabulary")
        if word[0].isupper() and not first:
            return RoutedToken(word, Label.PROPER, "capitalised mid-sentence")
        return RoutedToken(word, Label.ROMAN_KN, "unknown word", True)
