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

        visual_context_task = asyncio.create_task(self._maps.fetch_visual_context(payload))
        context_task = asyncio.create_task(
            self._maps.collect_location_signals(payload.lat, payload.lng)
        )

        visual_context, (location_context, landmarks) = await asyncio.gather(
            visual_context_task,
            context_task,
        )

        pitch_task = asyncio.create_task(
            self._ai.generate_broker_pitch(payload, lighting, location_context, landmarks)
        )
        render_task = asyncio.create_task(
            self._ai.generate_render(payload, lighting, visual_context, location_context, landmarks)
        )

        pitch, render_result = await asyncio.gather(pitch_task, render_task)
        context_notes = [*visual_context.notes]
        if render_result.fallback_reason:
            context_notes.append(render_result.fallback_reason)

        latency_ms = int((perf_counter() - started) * 1000)
        return PreviewResponse(
            address=payload.address,
            lat=payload.lat,
            lng=payload.lng,
            storey_level=payload.storey_level,
            altitude=payload.derived_altitude_m,
            heading=payload.heading,
            elevation_m=visual_context.elevation_m,
            camera_altitude_asl_m=visual_context.camera_altitude_asl_m,
            time_of_day=payload.time_of_day,
            lighting=lighting,
            landmarks=landmarks,
            context_notes=context_notes,
            pitch=pitch,
            street_view_image=bytes_to_data_url(visual_context.street_view),
            street_view_tilt_up_image=bytes_to_data_url(visual_context.street_view_tilt_up),
            satellite_image=bytes_to_data_url(visual_context.satellite),
            base_geometry_image=bytes_to_data_url(visual_context.base_geometry),
            base_geometry_source=visual_context.base_geometry_source,
            rendered_image=bytes_to_data_url(render_result.image),
            render_source=render_result.source,
            render_is_stock_fallback=render_result.is_stock_fallback,
            render_fallback_reason=render_result.fallback_reason,
            render_model=render_result.model_name,
            render_reference_count=render_result.reference_count,
            latency_ms=latency_ms,
        )
