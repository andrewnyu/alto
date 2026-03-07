from __future__ import annotations

import asyncio
from typing import Any

import googlemaps
import httpx

from app.core.config import Settings
from app.models.preview import PreviewRequest
from app.services.image_utils import tiny_placeholder_png


class MapsService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._mock_mode = settings.mock_mode
        self._maps_key = settings.google_maps_api_key
        self._http_timeout = settings.request_timeout_seconds
        self._gmaps = googlemaps.Client(key=self._maps_key) if self._maps_key else None

    async def fetch_base_geometry(self, payload: PreviewRequest) -> bytes:
        if self._mock_mode or not self._maps_key:
            return tiny_placeholder_png()

        street_view = await self._fetch_street_view(payload)
        if street_view:
            return street_view

        static_map = await self._fetch_static_map(payload)
        return static_map or tiny_placeholder_png()

    async def collect_location_signals(self, lat: float, lng: float) -> tuple[str, list[str]]:
        if self._mock_mode:
            return (
                f"Mock context around coordinates ({lat:.5f}, {lng:.5f}) with synthetic skyline signal.",
                ["Mock Tower", "Mock Marina", "Mock Cultural District"],
            )

        if not self._gmaps:
            return "No Google Maps context available.", []

        reverse_task = asyncio.create_task(asyncio.to_thread(self._reverse_geocode, lat, lng))
        places_task = asyncio.create_task(asyncio.to_thread(self._nearby_places, lat, lng))
        reverse_text, landmarks = await asyncio.gather(reverse_task, places_task, return_exceptions=False)

        landmark_text = ", ".join(landmarks[:5]) if landmarks else "No notable places returned"
        summary = f"Primary geo context: {reverse_text}. Nearby landmarks: {landmark_text}."
        return summary, landmarks

    async def geocode_address(self, address: str) -> tuple[str, float, float]:
        if self._mock_mode:
            return (f"Mock match for {address}", 37.79061, -122.39695)

        if not self._gmaps:
            raise ValueError("Google Maps geocoder is not configured")

        try:
            results = await asyncio.to_thread(self._geocode, address)
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc
        if not results:
            raise LookupError("No geocoding results")

        top = results[0]
        geometry = top.get("geometry", {})
        location = geometry.get("location", {})
        lat = location.get("lat")
        lng = location.get("lng")
        if not isinstance(lat, (float, int)) or not isinstance(lng, (float, int)):
            raise LookupError("Invalid geocoding result")
        formatted = top.get("formatted_address", address)
        return (str(formatted), float(lat), float(lng))

    def _reverse_geocode(self, lat: float, lng: float) -> str:
        try:
            results = self._gmaps.reverse_geocode((lat, lng)) if self._gmaps else []
            if not results:
                return f"coordinates ({lat:.5f}, {lng:.5f})"
            return results[0].get("formatted_address", f"coordinates ({lat:.5f}, {lng:.5f})")
        except Exception:
            return f"coordinates ({lat:.5f}, {lng:.5f})"

    def _nearby_places(self, lat: float, lng: float) -> list[str]:
        try:
            if not self._gmaps:
                return []
            result = self._gmaps.places_nearby(
                location=(lat, lng),
                radius=1800,
                keyword="luxury skyline landmark",
            )
            names = [place.get("name", "") for place in result.get("results", [])]
            cleaned = [name for name in names if name]
            return cleaned[:6]
        except Exception:
            return []

    def _geocode(self, address: str) -> list[dict[str, Any]]:
        return self._gmaps.geocode(address) if self._gmaps else []

    @staticmethod
    def _altitude_to_zoom(altitude: float) -> int:
        # 0m -> zoom 20, 500m -> zoom 14
        zoom = 20 - int(round((altitude / 500) * 6))
        return max(14, min(20, zoom))

    @staticmethod
    def _altitude_to_fov(altitude: float) -> int:
        # Higher altitude approximates a wider camera pullback in Street View terms.
        fov = int(round(95 - (altitude / 500) * 45))
        return max(35, min(100, fov))

    @staticmethod
    def _altitude_to_pitch(altitude: float) -> int:
        # Slightly increase downward pitch with altitude.
        pitch = int(round(-2 - (altitude / 500) * 14))
        return max(-20, min(20, pitch))

    async def _fetch_street_view(self, payload: PreviewRequest) -> bytes:
        params: dict[str, Any] = {
            "location": f"{payload.lat},{payload.lng}",
            "size": "640x360",
            "fov": self._altitude_to_fov(payload.altitude),
            "heading": int(round(payload.heading)) % 360,
            "pitch": self._altitude_to_pitch(payload.altitude),
            "source": "outdoor",
            "key": self._maps_key,
        }
        url = "https://maps.googleapis.com/maps/api/streetview"
        try:
            async with httpx.AsyncClient(timeout=self._http_timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
            return response.content
        except Exception:
            return b""

    async def _fetch_static_map(self, payload: PreviewRequest) -> bytes:
        params: dict[str, Any] = {
            "center": f"{payload.lat},{payload.lng}",
            "zoom": self._altitude_to_zoom(payload.altitude),
            "size": "640x360",
            "scale": 2,
            "maptype": "satellite",
            "format": "png",
            "key": self._maps_key,
        }
        if self._settings.google_map_id:
            params["map_id"] = self._settings.google_map_id

        url = "https://maps.googleapis.com/maps/api/staticmap"
        try:
            async with httpx.AsyncClient(timeout=self._http_timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
            return response.content
        except Exception:
            return b""
