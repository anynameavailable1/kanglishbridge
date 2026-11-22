import json
import logging
import threading
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from ..schemas import FeedbackRequest, TokenOverrideRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1")
_write_lock = threading.Lock()


@router.post("/feedback", status_code=201)
async def feedback(req: FeedbackRequest, request: Request) -> dict:
    """Stores a user correction locally (JSONL). It never changes model weights."""
    path = request.app.state.kb.settings.feedback_path
    record = {"ts": datetime.now(timezone.utc).isoformat(), **req.model_dump()}
    try:
        with _write_lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as exc:
        logger.exception("Could not store feedback")
        raise HTTPException(500, "Could not store feedback") from exc
    return {"stored": True}


@router.post("/tokens/override")
async def token_override(req: TokenOverrideRequest, request: Request) -> dict:
    """Manually correct a mis-routed word (e.g. mark 'bus' as english)."""
    try:
        request.app.state.kb.router.set_override(req.word, req.label)
    except (OSError, ValueError) as exc:
        logger.exception("Could not save override")
        raise HTTPException(500, "Could not save override") from exc
    return {"word": req.word.lower(), "label": req.label}
