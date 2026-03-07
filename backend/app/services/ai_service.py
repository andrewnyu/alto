from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
from typing import Any

import google.generativeai as genai

from app.core.config import Settings
from app.models.preview import LightingProfile, PreviewRequest
from app.services.maps_service import VisualContext


@dataclass(slots=True)
class RenderResult:
    image: bytes
    source: str
    is_stock_fallback: bool
    fallback_reason: str | None
    model_name: str
    reference_count: int


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
        visual_context: VisualContext,
        location_context: str,
        landmarks: list[str],
    ) -> RenderResult:
        references = self._build_reference_stack(payload, visual_context)
        reference_count = len(references)

        if self._mock_mode or not self._api_key:
            return RenderResult(
                image=visual_context.base_geometry,
                source="fallback_base_geometry",
                is_stock_fallback=True,
                fallback_reason="Nano Banana unavailable (mock mode or missing GEMINI_API_KEY).",
                model_name=self._image_model,
                reference_count=reference_count,
            )

        prompt = self._build_cinematographer_prompt(
            payload,
            lighting,
            visual_context,
            location_context,
            landmarks,
        )
        try:
            rendered, model_used = await asyncio.to_thread(
                self._generate_image_with_model_fallback,
                prompt,
                references,
            )
        except Exception as exc:
            return RenderResult(
                image=visual_context.base_geometry,
                source="fallback_base_geometry",
                is_stock_fallback=True,
                fallback_reason=f"Nano Banana generation failed: {str(exc)[:220]}",
                model_name=self._image_model,
                reference_count=reference_count,
            )

        if not rendered:
            return RenderResult(
                image=visual_context.base_geometry,
                source="fallback_base_geometry",
                is_stock_fallback=True,
                fallback_reason=(
                    "Nano Banana returned no image payload; using base geometry fallback."
                ),
                model_name=model_used,
                reference_count=reference_count,
            )

        matched_reference = self._detect_reference_echo(rendered, visual_context)
        if matched_reference:
            return RenderResult(
                image=rendered,
                source="reference_echo",
                is_stock_fallback=True,
                fallback_reason=(
                    f"Generated output matched {matched_reference}; likely stock fallback."
                ),
                model_name=model_used,
                reference_count=reference_count,
            )

        return RenderResult(
            image=rendered,
            source="nano_banana_generated",
            is_stock_fallback=False,
            fallback_reason=None,
            model_name=model_used,
            reference_count=reference_count,
        )

    def _build_reference_stack(
        self,
        payload: PreviewRequest,
        visual_context: VisualContext,
    ) -> list[bytes]:
        references: list[bytes] = []
        if payload.storey_level > 0:
            self._append_reference_once(references, visual_context.satellite)
            self._append_reference_once(references, visual_context.street_view_tilt_up)
            self._append_reference_once(references, visual_context.street_view)
            self._append_reference_once(references, visual_context.street_view_far_anchor)
        else:
            self._append_reference_once(references, visual_context.street_view)
            self._append_reference_once(references, visual_context.street_view_tilt_up)
            self._append_reference_once(references, visual_context.satellite)
        self._append_reference_once(references, visual_context.base_geometry)
        return references

    @staticmethod
    def _append_reference_once(references: list[bytes], candidate: bytes) -> None:
        if not candidate:
            return
        references.append(candidate)

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

    def _generate_image_with_model_fallback(
        self,
        prompt: str,
        references: list[bytes],
    ) -> tuple[bytes, str]:
        parts: list[Any] = [prompt]
        for image_bytes in references:
            if not image_bytes:
                continue
            parts.append(
                {
                    "mime_type": "image/png",
                    "data": image_bytes,
                }
            )

        model_candidates = self._image_model_candidates()
        last_exc: Exception | None = None
        for model_name in model_candidates:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(parts)
                image_bytes = self._extract_image_bytes(response)
                if image_bytes:
                    return image_bytes, model_name
            except Exception as exc:
                last_exc = exc
                if self._is_model_unavailable_error(exc):
                    continue
                raise

        if last_exc:
            raise RuntimeError(
                f"No usable image model from {model_candidates}. Last error: {str(last_exc)[:220]}"
            )
        return b"", model_candidates[0]

    def _image_model_candidates(self) -> list[str]:
        raw_candidates = [
            self._image_model,
            "gemini-flash-image-3",
            "gemini-3.1-flash-image-preview",
            "gemini-3-pro-image-preview",
            "gemini-2.5-flash-image",
            "gemini-2.0-flash-exp-image-generation",
        ]
        cleaned: list[str] = []
        for candidate in raw_candidates:
            if not candidate:
                continue
            normalized = candidate
            if normalized.startswith("models/"):
                normalized = normalized.split("/", 1)[1]
            if normalized not in cleaned:
                cleaned.append(normalized)
        return cleaned

    @staticmethod
    def _is_model_unavailable_error(exc: Exception) -> bool:
        message = str(exc).lower()
        return (
            "not found" in message
            or "is not supported" in message
            or "404" in message
            or "no longer available" in message
        )

    @staticmethod
    def _detect_reference_echo(rendered: bytes, visual_context: VisualContext) -> str | None:
        reference_candidates: list[tuple[str, bytes]] = [
            ("street_view", visual_context.street_view),
            ("street_view_tilt_up", visual_context.street_view_tilt_up),
            ("street_view_far_anchor", visual_context.street_view_far_anchor),
            ("satellite", visual_context.satellite),
            ("base_geometry", visual_context.base_geometry),
        ]
        for label, reference in reference_candidates:
            if reference and rendered == reference:
                return label
        return None

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
            f"Heading: {payload.heading} degrees. Storey level: {payload.storey_level}. "
            f"Camera altitude: {payload.derived_altitude_m}m. "
            f"Time of day: {payload.time_of_day.value}. Lighting profile: {lighting.prompt_note}. "
            f"Spatial context: {location_context}. Landmarks: {landmarks_text}."
        )

    def _build_cinematographer_prompt(
        self,
        payload: PreviewRequest,
        lighting: LightingProfile,
        visual_context: VisualContext,
        location_context: str,
        landmarks: list[str],
    ) -> str:
        landmarks_text = ", ".join(landmarks[:5]) if landmarks else "none provided"
        has_far_anchor = bool(visual_context.street_view_far_anchor)
        elevated_view = payload.storey_level > 0
        reference_guide = ""
        if elevated_view and has_far_anchor:
            reference_guide = (
                "Reference image #1 is satellite footprint/topology, #2 is tilt-up "
                "near Street View for facade verticals, #3 is near street-level view "
                "for immediate geometry, #4 is farther-offset Street View for depth "
                "continuity, and #5 is base geometry fallback. "
            )
        elif elevated_view:
            reference_guide = (
                "Reference image #1 is satellite footprint/topology, #2 is tilt-up "
                "near Street View for facade cues, #3 is near street-level view for "
                "immediate geometry, and #4 is base geometry fallback. "
            )
        else:
            reference_guide = (
                "Reference image #1 is near street-level context, #2 is tilt-up Street View, "
                "#3 is satellite footprint, and #4 is base geometry fallback. "
            )
        far_anchor_instruction = (
            "Infer mid-ground depth and partial occlusion from the farther-offset Street View "
            "capture while keeping road topology and massing plausible; this is anchored-imagined "
            "reconstruction, not exact survey geometry. "
            if has_far_anchor
            else ""
        )
        return (
            "These images are what can be seen from the street view of this building. "
            f"Estimate what can be seen from floor {payload.storey_level}. "
            "Make it beautiful and what a person would see when exploring the view. "
            "Take these reference captures and synthesize an elevated, hyper-realistic photograph. "
            "Apply realistic ray-traced reflections on a minimalist glass balcony railing in the "
            "foreground. Keep geometry aligned with the original camera perspective. "
            f"{reference_guide}"
            "For storey level > 0, camera must look forward at the horizon from balcony eye level. "
            f"Infer vertical uplift from storey level {payload.storey_level} "
            f"(approximately {payload.derived_altitude_m:.1f}m above base street level). "
            "Do not output top-down drone framing, and keep nearby roofline under 15% "
            "of frame area. "
            "Compose the render as an ultra-wide panoramic vista with strong left/right "
            "continuity, "
            "approximately 180-degree horizontal field-of-view feel, "
            "distant sea or skyline depth where plausible, and natural edge details suitable for "
            "horizontal panning interaction. "
            "Horizon line should sit around the upper-middle third of frame, not near the bottom. "
            "Prioritize a beautiful, premium vista with clean atmosphere, cinematic but natural "
            "color balance, and realistic long-range visibility. "
            "Avoid generic stock-photo composition, generic stock skyline clichés, or unrelated "
            "landmarks not supported by references. "
            f"{far_anchor_instruction}"
            f"{visual_context.viewpoint_note} "
            f"Location context: {location_context}. Landmarks: {landmarks_text}. "
            f"Storey level: {payload.storey_level}. "
            f"Camera altitude: {payload.derived_altitude_m}m. "
            f"{visual_context.terrain_note} "
            f"Estimated camera altitude above sea level: {visual_context.camera_altitude_asl_m}. "
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
            f"From storey {payload.storey_level} at roughly {payload.derived_altitude_m:.0f} "
            f"meters, this vantage frames {nearest} like a private asset class, not a postcard. "
            "If you need convincing, you are likely shopping below this bracket anyway."
        )
