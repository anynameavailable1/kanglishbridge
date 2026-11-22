"""Script-level tokenisation and sentence handling (pure Python, no models).

This module only separates *scripts* (Kannada Unicode / Latin / digits / symbols).
Deciding whether a Latin word is English or Romanized Kannada is token_router.py's job.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class TokenKind(str, Enum):
    SPACE = "space"
    SYMBOL = "symbol"
    NUMBER = "number"
    KANNADA_SCRIPT = "kannada_script"
    LATIN = "latin"


_TOKEN_RE = re.compile(
    r"""
    (?P<kn>[\u0C80-\u0CFF]+)
  | (?P<num>\d+(?:[.,:/\-]\d+)*)
  | (?P<latin>[A-Za-z]+(?:['\u2019][A-Za-z]+)*)
  | (?P<space>\s+)
  | (?P<sym>.)
    """,
    re.VERBOSE | re.DOTALL,
)
_OTHER_INDIC_RE = re.compile(r"[\u0900-\u0C7F\u0D00-\u0DFF]")
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?\u0964])\s+|\n+")


@dataclass
class Token:
    text: str
    kind: TokenKind


def clean_whitespace(text: str) -> str:
    """Collapse runs of spaces/tabs, trim ends. Words, punctuation, digits and emojis are untouched."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t\u00a0]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    return text.strip()


def tokenize(text: str) -> list[Token]:
    """Lossless: ''.join(t.text for t in tokenize(x)) == x."""
    kinds = {"kn": TokenKind.KANNADA_SCRIPT, "num": TokenKind.NUMBER, "latin": TokenKind.LATIN,
             "space": TokenKind.SPACE, "sym": TokenKind.SYMBOL}
    return [Token(m.group(), kinds[m.lastgroup]) for m in _TOKEN_RE.finditer(text)]


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_SPLIT_RE.split(text) if s and s.strip()]


def has_other_indic_script(text: str) -> bool:
    return bool(_OTHER_INDIC_RE.search(text))
