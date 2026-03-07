from __future__ import annotations

import asyncio
from time import perf_counter

from app.models.preview import PreviewRequest, PreviewResponse
from app.services.ai_service import AIService
from app.services.image_utils import bytes_to_data_url
from app.services.lumen_engine import LumenEngine
from app.services.maps_service import MapsService


class PreviewOrchestrator:
    def __init__(self, maps_service: MapsService, ai_service: AIService) -> None:
        self._maps = maps_service
        self._ai = ai_service

    async def generate_preview(self, payload: PreviewRequest) -> PreviewResponse:
        started = perf_counter()
        lighting = LumenEngine.profile_for(payload.time_of_day)

        base_geometry_task = asyncio.create_task(self._maps.fetch_base_geometry(payload))
        context_task = asyncio.create_task(self._maps.collect_location_signals(payload.lat, payload.lng))

        base_geometry, (location_context, landmarks) = await asyncio.gather(
            base_geometry_task,
            context_task,
        )

        pitch_task = asyncio.create_task(
            self._ai.generate_broker_pitch(payload, lighting, location_context, landmarks)
        )
        render_task = asyncio.create_task(self._ai.generate_render(payload, lighting, base_geometry))

        pitch, rendered = await asyncio.gather(pitch_task, render_task)

        latency_ms = int((perf_counter() - started) * 1000)
        return PreviewResponse(
            address=payload.address,
            lat=payload.lat,
            lng=payload.lng,
            altitude=payload.altitude,
            heading=payload.heading,
            time_of_day=payload.time_of_day,
            lighting=lighting,
            landmarks=landmarks,
            pitch=pitch,
            base_geometry_image=bytes_to_data_url(base_geometry),
            rendered_image=bytes_to_data_url(rendered),
            latency_ms=latency_ms,
        )
