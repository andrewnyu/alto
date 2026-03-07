from __future__ import annotations

import asyncio
import base64
from typing import Any

import google.generativeai as genai

from app.core.config import Settings
from app.models.preview import LightingProfile, PreviewRequest


class AIService:
    def __init__(self, settings: Settings) -> None:
        self._mock_mode = settings.mock_mode
        self._api_key = settings.gemini_api_key
        self._text_model = settings.gemini_model
        self._image_model = settings.nano_banana_model

        if self._api_key:
            genai.configure(api_key=self._api_key)

    async def generate_broker_pitch(
        self,
        payload: PreviewRequest,
        lighting: LightingProfile,
        location_context: str,
        landmarks: list[str],
    ) -> str:
        if self._mock_mode or not self._api_key:
            return self._fallback_pitch(payload, landmarks)

        prompt = self._build_broker_prompt(payload, lighting, location_context, landmarks)
        try:
            return await asyncio.to_thread(self._generate_text, prompt)
        except Exception:
            return self._fallback_pitch(payload, landmarks)

    async def generate_render(
        self,
        payload: PreviewRequest,
        lighting: LightingProfile,
        base_geometry: bytes,
    ) -> bytes:
        if self._mock_mode or not self._api_key:
            return base_geometry

        prompt = self._build_cinematographer_prompt(payload, lighting)
        try:
            rendered = await asyncio.to_thread(self._generate_image, prompt, base_geometry)
            return rendered or base_geometry
        except Exception:
            return base_geometry

    def _generate_text(self, prompt: str) -> str:
        model = genai.GenerativeModel(self._text_model)
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.9, "max_output_tokens": 180},
        )
        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()
        return "An elevated perspective with obvious scarcity value and commanding visual equity. Acquire now before comparable inventory is priced for someone else."  # noqa: E501

    def _generate_image(self, prompt: str, base_geometry: bytes) -> bytes:
        model = genai.GenerativeModel(self._image_model)
        response = model.generate_content(
            [
                prompt,
                {
                    "mime_type": "image/png",
                    "data": base_geometry,
                },
            ]
        )
        return self._extract_image_bytes(response)

    def _extract_image_bytes(self, response: Any) -> bytes:
        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            for part in parts:
                inline_data = getattr(part, "inline_data", None)
                if not inline_data:
                    continue
                data = getattr(inline_data, "data", None)
                if isinstance(data, bytes):
                    return data
                if isinstance(data, str):
                    try:
                        return base64.b64decode(data)
                    except Exception:
                        continue
        return b""

    def _build_broker_prompt(
        self,
        payload: PreviewRequest,
        lighting: LightingProfile,
        location_context: str,
        landmarks: list[str],
    ) -> str:
        landmarks_text = ", ".join(landmarks[:5]) if landmarks else "none provided"
        return (
            "You are the Lead Broker for ALTO. You view luxury buildings as 'high-value specimen "
            "containers.' You are witty, slightly condescending, and persuasive. "
            "Write exactly 2 sentences for this specific view. "
            f"Address: {payload.address}. Coordinates: ({payload.lat}, {payload.lng}). "
            f"Heading: {payload.heading} degrees. Altitude: {payload.altitude}m. "
            f"Time of day: {payload.time_of_day.value}. Lighting profile: {lighting.prompt_note}. "
            f"Spatial context: {location_context}. Landmarks: {landmarks_text}."
        )

    def _build_cinematographer_prompt(self, payload: PreviewRequest, lighting: LightingProfile) -> str:
        return (
            "Take this raw 3D mesh geometry. Transform it into a hyper-realistic photograph. "
            "Apply realistic ray-traced reflections on a minimalist glass balcony railing in the "
            "foreground. Keep geometry aligned with the original camera perspective. "
            f"Lighting for {payload.time_of_day.value}: {lighting.prompt_note}. "
            "Sunrise: 2500K, low-angle light, morning mist. "
            "GoldenHour: 3000K, intense bloom, long shadows. "
            "Midnight: 5000K point lights, high-ISO cinematic grain. "
            "Preserve urban realism, nuanced material textures, and premium architectural finish."
        )

    @staticmethod
    def _fallback_pitch(payload: PreviewRequest, landmarks: list[str]) -> str:
        nearest = landmarks[0] if landmarks else "the dominant skyline"
        return (
            f"From {payload.altitude:.0f} meters, this vantage frames {nearest} like a private asset class, not a postcard. "
            "If you need convincing, you are likely shopping below this bracket anyway."
        )
