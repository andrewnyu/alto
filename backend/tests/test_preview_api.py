from fastapi.testclient import TestClient

from app.main import create_app
from app.models.preview import LightingProfile, PreviewResponse, TimeOfDay


class FakeOrchestrator:
    async def generate_preview(self, payload):
        return PreviewResponse(
            address=payload.address,
            lat=payload.lat,
            lng=payload.lng,
            altitude=payload.altitude,
            heading=payload.heading,
            time_of_day=payload.time_of_day,
            lighting=LightingProfile(
                kelvin=3000,
                shadow_length_multiplier=1.0,
                atmospheric_haze=0.2,
                bloom_intensity=0.3,
                iso_grain=0.1,
                prompt_note="test note",
            ),
            landmarks=["Test Tower"],
            pitch="Two-sentence luxury pitch.",
            base_geometry_image="data:image/png;base64,AAAAAAAAAAAAAAAAAAAAAA==",
            rendered_image="data:image/png;base64,BBBBBBBBBBBBBBBBBBBBBB==",
            latency_ms=123,
        )


def test_preview_endpoint_accepts_request_and_returns_response() -> None:
    app = create_app()
    with TestClient(app) as client:
        app.state.preview_orchestrator = FakeOrchestrator()
        response = client.post(
            "/api/v1/preview",
            json={
                "address": "1 Market St, San Francisco, CA",
                "lat": 37.7936,
                "lng": -122.395,
                "altitude": 140,
                "heading": 180,
                "time_of_day": TimeOfDay.GOLDEN_HOUR.value,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["pitch"] == "Two-sentence luxury pitch."
    assert payload["time_of_day"] == TimeOfDay.GOLDEN_HOUR.value
