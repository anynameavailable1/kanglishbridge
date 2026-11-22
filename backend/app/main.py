"""FastAPI application factory.  Run:  uvicorn app.main:app --host 127.0.0.1 --port 8000"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from .api import datasets, feedback, health, translate
from .config import Settings, load_settings
from .nlp.pipeline import TranslationPipeline, build_default_pipeline, build_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("kanglishbridge")


@dataclass
class AppState:
    settings: Settings
    router: object
    pipeline: TranslationPipeline | None = None
    ready: bool = False
    message: str = "Models are loading"
    device: str = "unknown"
    model_status: dict = field(default_factory=lambda: {"transliterator": "loading", "translator": "loading"})
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


def _load_models(state: AppState) -> None:
    """Blocking; runs once in a worker thread at startup. Errors are logged and reported by /health."""
    try:
        state.pipeline = build_default_pipeline(state.settings, state.router)
        state.device = state.pipeline.translator.device
        state.model_status = {"transliterator": "ready", "translator": "ready"}
        state.ready, state.message = True, "Models ready"
        logger.info("All models loaded")
    except Exception as exc:
        logger.exception("Model loading failed")
        state.model_status = {"transliterator": "error", "translator": "error"}
        state.message = f"Model loading failed ({type(exc).__name__}); see backend log and README troubleshooting"


def create_app(settings: Settings | None = None, pipeline: TranslationPipeline | None = None) -> FastAPI:
    settings = settings or load_settings()
    state = AppState(settings=settings, router=pipeline.router if pipeline else build_router(settings))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        task = None
        if pipeline is not None:  # injected pipeline (tests only)
            state.pipeline, state.ready, state.message = pipeline, True, "Injected pipeline"
            state.model_status = {"transliterator": "injected", "translator": "injected"}
        elif settings.skip_model_load:
            state.message = "Model loading skipped (KB_SKIP_MODEL_LOAD=1)"
            state.model_status = {"transliterator": "skipped", "translator": "skipped"}
        else:
            task = asyncio.create_task(run_in_threadpool(_load_models, state))
        yield
        logger.info("Shutting down")
        if task is not None and not task.done():
            task.cancel()  # a model download in a worker thread cannot be interrupted; process exit ends it
        state.pipeline, state.ready = None, False

    app = FastAPI(title="KanglishBridge API", version="1.0.0", lifespan=lifespan)
    app.state.kb = state
    app.add_middleware(CORSMiddleware, allow_origin_regex=settings.cors_origin_regex,
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
    app.include_router(health.router)
    app.include_router(translate.router)
    app.include_router(feedback.router)
    app.include_router(datasets.router)
    return app


app = create_app()
