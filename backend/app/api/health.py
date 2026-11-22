from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health(request: Request) -> dict:
    s = request.app.state.kb
    return {"status": "ok", "models_ready": s.ready, "models": dict(s.model_status),
            "device": s.device, "message": s.message}
