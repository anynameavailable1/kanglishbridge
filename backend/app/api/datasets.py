import logging

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from ..data_tools import load_dataset, validate_dataframe

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/datasets")


@router.post("/validate")
async def validate(request: Request, file: UploadFile = File(...)) -> dict:
    """Validates an uploaded CSV/JSONL. The file is analysed in memory and not stored."""
    name = (file.filename or "").lower()
    fmt = "csv" if name.endswith(".csv") else "jsonl" if name.endswith((".jsonl", ".json")) else None
    if fmt is None:
        raise HTTPException(415, "Upload a .csv or .jsonl file")
    limit = request.app.state.kb.settings.max_upload_bytes
    raw = await file.read(limit + 1)
    if len(raw) > limit:
        raise HTTPException(413, "File too large")
    try:
        df = load_dataset(raw, fmt)
    except Exception as exc:  # pandas raises many parser-specific errors
        logger.warning("Dataset parse failed: %s", type(exc).__name__)
        raise HTTPException(422, "Could not parse the file as UTF-8 CSV/JSONL") from exc
    return validate_dataframe(df)
