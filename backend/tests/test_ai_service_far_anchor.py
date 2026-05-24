from __future__ import annotations

import pytest

from app.core.config import Settings
from app.models.preview import LightingProfile, PreviewRequest, TimeOfDay
from app.services.ai_service import AIService
from app.services.maps_service import VisualContext


def build_ai_service() -> AIService:
    settings = Settings(
        mock_mode=False,
        gemini_api_key="test-gemini-key",
        google_maps_api_key="AIza-test-google-key",
    )
    return AIService(settings)


def build_payload() -> PreviewRequest:
    return PreviewRequest(
        address="181 Fremont St, San Francisco, CA",
        lat=37.79061,
        lng=-122.39695,
        storey_level=18,
        heading=150.0,
        time_of_day=TimeOfDay.GOLDEN_HOUR,
    )


def build_lighting() -> LightingProfile:
    return LightingProfile(
        kelvin=3000,
        shadow_length_multiplier=1.2,
        atmospheric_haze=0.2,
        bloom_intensity=0.3,
        iso_grain=0.15,
        prompt_note="warm cinematic glow",
    )


def build_visual_context(has_far_anchor: bool) -> VisualContext:
    return VisualContext(
        street_view=b"street",
        street_view_tilt_up=b"tilt-up",
        street_view_far_anchor=b"far-anchor" if has_far_anchor else b"",
        satellite=b"satellite",
        base_geometry=b"base-geometry",
        base_geometry_source="satellite",
        elevation_m=24.5,
        camera_altitude_asl_m=82.1,
        terrain_note="Terrain elevation near site: 24.5m above sea level.",
        viewpoint_note=(
            "For non-ground storeys, compose from satellite footprint and elevation-based vantage. "
            "Use far-anchor street view for depth/occlusion and tilt-up street view for facade "
            "realism and vanishing lines."
        ),
        far_anchor_note="Far Street View anchor selected at 130m (score 0.91).",
        far_anchor_distance_m=130.0,
        notes=[],
    )


def test_broker_prompt_requests_restrained_skyline_narrative() -> None:
    ai_service = build_ai_service()
    prompt = ai_service._build_broker_prompt(
        payload=build_payload(),
        lighting=build_lighting(),
        location_context="San Francisco skyline context",
        landmarks=["Salesforce Tower"],
    )

    assert "clear, factual, and restrained tone" in prompt
    assert "jokes, sarcasm, snark" in prompt
    assert "luxury-broker hype" in prompt
    assert "investment language" in prompt
    assert "Write exactly 2 sentences" in prompt


def test_fallback_pitch_is_neutral_skyline_narrative() -> None:
    fallback = AIService._fallback_pitch(build_payload(), ["Salesforce Tower"])

    assert "Salesforce Tower" in fallback
    assert "Acquire now" not in fallback
    assert "scarcity value" not in fallback
    assert "investment" not in fallback


@pytest.mark.asyncio
async def test_generate_render_uses_far_anchor_reference_order_and_prompt_guidance(
    monkeypatch,
) -> None:
    ai_service = build_ai_service()
    payload = build_payload()
    lighting = build_lighting()
    visual_context = build_visual_context(has_far_anchor=True)
    captured: dict[str, object] = {}

    def fake_generate_image(prompt: str, references: list[bytes]) -> tuple[bytes, str]:
        captured["prompt"] = prompt
        captured["references"] = references
        return b"rendered", "gemini-flash-image-3"

    monkeypatch.setattr(ai_service, "_generate_image_with_model_fallback", fake_generate_image)

    render_result = await ai_service.generate_render(
        payload=payload,
        lighting=lighting,
        visual_context=visual_context,
        location_context="San Francisco skyline context",
        landmarks=["Salesforce Tower"],
    )

    assert render_result.image == b"rendered"
    assert render_result.source == "nano_banana_generated"
    assert render_result.is_stock_fallback is False
    assert render_result.model_name
    assert render_result.reference_count == 5
    assert captured["references"] == [
        b"satellite",
        b"tilt-up",
        b"street",
        b"far-anchor",
        b"base-geometry",
    ]
    prompt = captured["prompt"]
    assert isinstance(prompt, str)
    assert "These images are what can be seen from the street view of this building." in prompt
    assert "Estimate what can be seen from floor 18." in prompt
    assert "Make it beautiful and what a person would see when exploring the view." in prompt
    assert "Reference image #1 is satellite footprint/topology" in prompt
    assert "#5 is base geometry fallback." in prompt
    assert "keep nearby roofline under 15% of frame area" in prompt
    assert "Avoid generic stock-photo composition" in prompt
    assert "Infer vertical uplift from storey level 18" in prompt
    assert "anchored-imagined reconstruction, not exact survey geometry" in prompt


@pytest.mark.asyncio
async def test_generate_render_omits_far_anchor_when_unavailable(monkeypatch) -> None:
    ai_service = build_ai_service()
    payload = build_payload()
    lighting = build_lighting()
    visual_context = build_visual_context(has_far_anchor=False)
    captured: dict[str, object] = {}

    def fake_generate_image(prompt: str, references: list[bytes]) -> tuple[bytes, str]:
        captured["prompt"] = prompt
        captured["references"] = references
        return b"rendered", "gemini-flash-image-3"

    monkeypatch.setattr(ai_service, "_generate_image_with_model_fallback", fake_generate_image)

    render_result = await ai_service.generate_render(
        payload=payload,
        lighting=lighting,
        visual_context=visual_context,
        location_context="San Francisco skyline context",
        landmarks=["Salesforce Tower"],
    )

    assert render_result.image == b"rendered"
    assert render_result.source == "nano_banana_generated"
    assert render_result.is_stock_fallback is False
    assert render_result.reference_count == 4
    assert captured["references"] == [
        b"satellite",
        b"tilt-up",
        b"street",
        b"base-geometry",
    ]
    prompt = captured["prompt"]
    assert isinstance(prompt, str)
    assert "Estimate what can be seen from floor 18." in prompt
    assert "Reference image #4 is farther-offset Street View" not in prompt
    assert "Reference image #1 is satellite footprint/topology" in prompt


@pytest.mark.asyncio
async def test_generate_render_flags_reference_echo_as_stock_fallback(monkeypatch) -> None:
    ai_service = build_ai_service()
    payload = build_payload()
    lighting = build_lighting()
    visual_context = build_visual_context(has_far_anchor=True)

    def fake_generate_image(prompt: str, references: list[bytes]) -> tuple[bytes, str]:
        _ = prompt
        _ = references
        return b"street", "gemini-flash-image-3"

    monkeypatch.setattr(ai_service, "_generate_image_with_model_fallback", fake_generate_image)

    render_result = await ai_service.generate_render(
        payload=payload,
        lighting=lighting,
        visual_context=visual_context,
        location_context="San Francisco skyline context",
        landmarks=["Salesforce Tower"],
    )

    assert render_result.source == "reference_echo"
    assert render_result.is_stock_fallback is True
    assert render_result.fallback_reason
    assert "street_view" in render_result.fallback_reason
