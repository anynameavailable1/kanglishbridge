import asyncio
import logging

from fastapi import APIRouter, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from ..nlp.base import InferenceError
from ..schemas import TranslateRequest, TranslateResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1")


@router.post("/translate", response_model=TranslateResponse)
async def translate(req: TranslateRequest, request: Request) -> dict:
    s = request.app.state.kb
    if not s.ready:
        raise HTTPException(503, s.message or "Models are not ready yet")
    if len(req.text) > s.settings.max_text_chars:
        raise HTTPException(413, f"Text exceeds {s.settings.max_text_chars} characters")
    try:
        async with s.lock:  # one inference at a time; keeps CPU usage predictable
            return await asyncio.wait_for(run_in_threadpool(s.pipeline.process, req.text),
                                          timeout=s.settings.request_timeout_s)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except asyncio.TimeoutError as exc:
        logger.error("Translation timed out")
        raise HTTPException(504, "Translation timed out") from exc
    except InferenceError as exc:
        logger.exception("Inference error")
        raise HTTPException(500, "The translation model failed; see server log") from exc
