from __future__ import annotations

import pytest

from app.core.config import Settings
from app.models.preview import PreviewRequest, TimeOfDay
from app.services.maps_service import MapsService


def build_maps_service() -> MapsService:
    settings = Settings(
        mock_mode=False,
        google_maps_api_key="AIza-test-google-key",
        far_streetview_enabled=True,
        far_streetview_probe_radius_m=120,
    )
    return MapsService(settings)


def test_build_far_anchor_candidates_uses_expected_bearings_and_distances() -> None:
    lat = 37.79061
    lng = -122.39695
    heading = 150.0
    desired_offset = MapsService._desired_far_offset_m(64.0)

    candidates = MapsService._build_far_anchor_candidates(lat, lng, heading, desired_offset)

    assert len(candidates) == 4
    assert [round(candidate[2], 1) for candidate in candidates] == [330.0, 305.0, 355.0, 330.0]

    for candidate_lat, candidate_lng, _, candidate_distance in candidates:
        measured_distance = MapsService._haversine_distance_m(
            lat,
            lng,
            candidate_lat,
            candidate_lng,
        )
        assert measured_distance == pytest.approx(candidate_distance, rel=0.03)


def test_score_far_anchor_candidate_prefers_aligned_and_distance_fit() -> None:
    service = build_maps_service()
    payload = PreviewRequest(
        address="181 Fremont St, San Francisco, CA",
        lat=37.79061,
        lng=-122.39695,
        storey_level=18,
        heading=150.0,
        time_of_day=TimeOfDay.GOLDEN_HOUR,
    )
    desired_offset = MapsService._desired_far_offset_m(payload.derived_altitude_m)

    aligned_anchor = MapsService._destination_point(
        payload.lat,
        payload.lng,
        (payload.heading + 180.0) % 360.0,
        desired_offset,
    )
    misaligned_anchor = MapsService._destination_point(
        payload.lat,
        payload.lng,
        0.0,
        desired_offset * 1.25,
    )

    aligned_score = service._score_far_anchor_candidate(
        payload,
        desired_offset,
        {"status": "OK", "location": {"lat": aligned_anchor[0], "lng": aligned_anchor[1]}},
    )
    misaligned_score = service._score_far_anchor_candidate(
        payload,
        desired_offset,
        {"status": "OK", "location": {"lat": misaligned_anchor[0], "lng": misaligned_anchor[1]}},
    )

    assert aligned_score is not None
    assert misaligned_score is not None
    assert aligned_score.score > misaligned_score.score
    assert aligned_score.alignment > misaligned_score.alignment


@pytest.mark.asyncio
async def test_fetch_visual_context_selects_far_anchor_and_appends_note(monkeypatch) -> None:
    service = build_maps_service()
    payload = PreviewRequest(
        address="181 Fremont St, San Francisco, CA",
        lat=37.79061,
        lng=-122.39695,
        storey_level=20,
        heading=150.0,
        time_of_day=TimeOfDay.GOLDEN_HOUR,
    )

    async def fake_fetch_street_view(
        payload: PreviewRequest,
        pitch_override: int | None = None,
        fov_override: int | None = None,
        location_override: tuple[float, float] | None = None,
    ) -> bytes:
        if location_override is not None:
            return b"far-anchor"
        if pitch_override is not None:
            return b"tilt-up"
        return b"street"

    async def fake_fetch_static_map(_: PreviewRequest) -> bytes:
        return b"satellite"

    async def fake_fetch_street_view_metadata(lat: float, lng: float, radius_m: int):
        assert radius_m == 120
        return {"status": "OK", "location": {"lat": lat, "lng": lng}}

    monkeypatch.setattr(service, "_fetch_street_view", fake_fetch_street_view)
    monkeypatch.setattr(service, "_fetch_static_map", fake_fetch_static_map)
    monkeypatch.setattr(service, "_fetch_street_view_metadata", fake_fetch_street_view_metadata)
    monkeypatch.setattr(service, "_elevation", lambda *_: 24.5)

    visual_context = await service.fetch_visual_context(payload)

    assert visual_context.street_view == b"street"
    assert visual_context.street_view_tilt_up == b"tilt-up"
    assert visual_context.street_view_far_anchor == b"far-anchor"
    assert visual_context.satellite == b"satellite"
    assert visual_context.base_geometry_source == "street_view_tilt_up"
    assert visual_context.far_anchor_distance_m is not None
    assert any("Far Street View anchor selected" in note for note in visual_context.notes)


@pytest.mark.asyncio
async def test_fetch_visual_context_gracefully_falls_back_when_far_anchor_unavailable(
    monkeypatch,
) -> None:
    service = build_maps_service()
    payload = PreviewRequest(
        address="181 Fremont St, San Francisco, CA",
        lat=37.79061,
        lng=-122.39695,
        storey_level=20,
        heading=150.0,
        time_of_day=TimeOfDay.GOLDEN_HOUR,
    )

    async def fake_fetch_street_view(
        payload: PreviewRequest,
        pitch_override: int | None = None,
        fov_override: int | None = None,
        location_override: tuple[float, float] | None = None,
    ) -> bytes:
        if location_override is not None:
            return b""
        if pitch_override is not None:
            return b"tilt-up"
        return b"street"

    async def fake_fetch_static_map(_: PreviewRequest) -> bytes:
        return b"satellite"

    async def fake_fetch_street_view_metadata(_: float, __: float, radius_m: int):
        assert radius_m == 120
        return {"status": "ZERO_RESULTS"}

    monkeypatch.setattr(service, "_fetch_street_view", fake_fetch_street_view)
    monkeypatch.setattr(service, "_fetch_static_map", fake_fetch_static_map)
    monkeypatch.setattr(service, "_fetch_street_view_metadata", fake_fetch_street_view_metadata)
    monkeypatch.setattr(service, "_elevation", lambda *_: 24.5)

    visual_context = await service.fetch_visual_context(payload)

    assert visual_context.street_view_far_anchor == b""
    assert visual_context.base_geometry_source == "street_view_tilt_up"
    assert visual_context.far_anchor_distance_m is None
    assert any("Far Street View anchor unavailable" in note for note in visual_context.notes)
