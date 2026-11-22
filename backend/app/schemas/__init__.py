from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TranslateRequest(BaseModel):
    text: str = Field(..., description="Romanized Kannada / Kanglish / Kannada text")

    @field_validator("text")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be empty")
        return v


class TokenInfo(BaseModel):
    text: str
    label: str


class TranslateResponse(BaseModel):
    original_text: str
    detected_languages: list[str]
    normalized_text: str
    translated_text: str
    warnings: list[str]
    tokens: list[TokenInfo] = []
    latency_ms: dict[str, float] = {}


class FeedbackRequest(BaseModel):
    original_text: str = Field(..., min_length=1, max_length=5000)
    model_translation: str = Field("", max_length=5000)
    corrected_translation: str = Field(..., min_length=1, max_length=5000)
    comment: str = Field("", max_length=1000)


class TokenOverrideRequest(BaseModel):
    word: str = Field(..., pattern=r"^[A-Za-z']{1,40}$")
    label: Literal["english", "romanized_kannada", "proper_noun"]
