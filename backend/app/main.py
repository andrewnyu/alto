from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.preview import router as preview_router
from app.core.config import Settings, get_settings
from app.services.ai_service import AIService
from app.services.maps_service import MapsService
from app.services.orchestrator import PreviewOrchestrator


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        maps_service = MapsService(resolved_settings)
        ai_service = AIService(resolved_settings)
        app.state.maps_service = maps_service
        app.state.ai_service = ai_service
        app.state.preview_orchestrator = PreviewOrchestrator(maps_service, ai_service)
        yield

    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(preview_router)

    @app.get("/healthz", tags=["health"])
    async def healthz() -> dict[str, str | bool]:
        nano_banana_available = bool(
            resolved_settings.gemini_api_key and not resolved_settings.mock_mode
        )
        return {
            "status": "ok",
            "nano_banana_available": nano_banana_available,
            "nano_banana_model": resolved_settings.nano_banana_model,
            "mock_mode": resolved_settings.mock_mode,
        }

    return app


app = create_app()
