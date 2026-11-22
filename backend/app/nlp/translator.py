"""AI4Bharat IndicTrans2 (indic -> en, distilled 200M) wrapper.

Follows the usage documented on the model card:
https://huggingface.co/ai4bharat/indictrans2-indic-en-dist-200M
"""
from __future__ import annotations

import logging

from .base import BaseTranslator, InferenceError, ModelLoadError

logger = logging.getLogger(__name__)
SRC_LANG, TGT_LANG = "kan_Knda", "eng_Latn"


class IndicTrans2Translator(BaseTranslator):
    name = "ai4bharat-indictrans2"

    def __init__(self, model_id: str = "ai4bharat/indictrans2-indic-en-dist-200M", device: str = "auto",
                 num_beams: int = 5, max_length: int = 256, batch_size: int = 8) -> None:
        self.model_id, self.num_beams, self.max_length, self.batch_size = model_id, num_beams, max_length, batch_size
        self.requested_device = device
        self.device = "cpu"
        self.model = self.tokenizer = self.processor = None
        self._torch = None

    def load(self) -> None:
        try:
            import torch
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            try:
                from IndicTransToolkit.processor import IndicProcessor
            except ImportError:  # older toolkit layout
                from IndicTransToolkit import IndicProcessor
        except ImportError as exc:
            raise ModelLoadError("torch / transformers / IndicTransToolkit are not installed") from exc
        self._torch = torch
        want = self.requested_device
        self.device = "cuda" if (want in ("auto", "cuda") and torch.cuda.is_available()) else "cpu"
        if want == "cuda" and self.device == "cpu":
            logger.warning("CUDA requested but unavailable; falling back to CPU")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_id, trust_remote_code=True)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                self.model_id, trust_remote_code=True,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            ).to(self.device).eval()
            self.processor = IndicProcessor(inference=True)
        except Exception as exc:
            logger.exception("IndicTrans2 failed to load")
            raise ModelLoadError("IndicTrans2 failed to load (check network for first download, see README)") from exc
        logger.info("IndicTrans2 loaded on %s", self.device)

    def translate(self, sentences: list[str]) -> list[str]:
        if self.model is None:
            raise InferenceError("IndicTrans2 is not loaded")
        results: list[str] = []
        try:
            for i in range(0, len(sentences), self.batch_size):
                batch = self.processor.preprocess_batch(sentences[i:i + self.batch_size],
                                                        src_lang=SRC_LANG, tgt_lang=TGT_LANG)
                inputs = self.tokenizer(batch, truncation=True, padding="longest", return_tensors="pt",
                                        return_attention_mask=True).to(self.device)
                with self._torch.inference_mode():
                    out = self.model.generate(**inputs, use_cache=True, min_length=0, max_length=self.max_length,
                                              num_beams=self.num_beams, num_return_sequences=1)
                decoded = self.tokenizer.batch_decode(out, skip_special_tokens=True,
                                                      clean_up_tokenization_spaces=True)
                results.extend(self.processor.postprocess_batch(decoded, lang=TGT_LANG))
        except Exception as exc:
            logger.exception("IndicTrans2 inference failed")
            raise InferenceError("Translation model failed during inference") from exc
        return results
