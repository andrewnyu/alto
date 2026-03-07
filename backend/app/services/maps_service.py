from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from typing import Any

import googlemaps
import httpx

from app.core.config import Settings
from app.models.preview import PreviewRequest
from app.services.image_utils import tiny_placeholder_png

EARTH_RADIUS_M = 6_371_000.0


@dataclass(slots=True)
class VisualContext:
    street_view: bytes
    street_view_tilt_up: bytes
    street_view_far_anchor: bytes
    satellite: bytes
    base_geometry: bytes
    base_geometry_source: str
    elevation_m: float | None
    camera_altitude_asl_m: float | None
    terrain_note: str
    viewpoint_note: str
    far_anchor_note: str | None
    far_anchor_distance_m: float | None
    notes: list[str]


@dataclass(slots=True)
class FarAnchorResult:
    image: bytes
    note: str | None
    distance_m: float | None


@dataclass(slots=True)
class FarAnchorCandidate:
    pano_lat: float
    pano_lng: float
    pano_distance_m: float
    alignment: float
    distance_fit: float
    score: float


class MapsService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._mock_mode = settings.mock_mode
        self._maps_key = settings.google_maps_api_key
        self._http_timeout = settings.request_timeout_seconds
        self._gmaps = googlemaps.Client(key=self._maps_key) if self._maps_key else None

    async def fetch_visual_context(self, payload: PreviewRequest) -> VisualContext:
        placeholder = tiny_placeholder_png()
        if self._mock_mode or not self._maps_key:
            return VisualContext(
                street_view=placeholder,
                street_view_tilt_up=placeholder,
                street_view_far_anchor=b"",
                satellite=placeholder,
                base_geometry=placeholder,
                base_geometry_source="placeholder",
                elevation_m=None,
                camera_altitude_asl_m=None,
                terrain_note="Elevation unavailable (mock mode or missing API key).",
                viewpoint_note="Use satellite composition with elevated vantage approximation.",
                far_anchor_note=None,
                far_anchor_distance_m=None,
                notes=["Mock mode active; Google imagery/elevation APIs not called."],
            )

        street_task = asyncio.create_task(self._fetch_street_view(payload))
        street_tilt_up_task = asyncio.create_task(
            self._fetch_street_view(
                payload,
                pitch_override=self._storey_to_pitch_up(payload.storey_level),
            )
        )
        satellite_task = asyncio.create_task(self._fetch_static_map(payload))
        elevation_task = asyncio.create_task(
            asyncio.to_thread(self._elevation, payload.lat, payload.lng)
        )
        far_anchor_task = asyncio.create_task(self._fetch_far_street_view_anchor(payload))

        street_raw, street_tilt_up_raw, satellite_raw, elevation_m, far_anchor_result = (
            await asyncio.gather(
                street_task,
                street_tilt_up_task,
                satellite_task,
                elevation_task,
                far_anchor_task,
            )
        )

        street = street_raw or placeholder
        street_tilt_up = street_tilt_up_raw or street or placeholder
        satellite = satellite_raw or placeholder
        notes: list[str] = []
        if not satellite_raw:
            notes.append(
                "Satellite imagery unavailable from Maps Static API. "
                "Enable Maps Static API for satellite-guided elevated synthesis."
            )
        if not street_raw and not street_tilt_up_raw:
            notes.append("Street View imagery unavailable for facade grounding.")
        if elevation_m is None:
            notes.append("Elevation API unavailable; camera altitude above sea level is estimated.")
        if far_anchor_result.note:
            notes.append(far_anchor_result.note)

        base_geometry_source = "placeholder"
        if payload.storey_level > 0:
            if street_tilt_up_raw:
                base_geometry = street_tilt_up_raw
                base_geometry_source = "street_view_tilt_up"
            elif street_raw:
                base_geometry = street_raw
                base_geometry_source = "street_view"
            elif far_anchor_result.image:
                base_geometry = far_anchor_result.image
                base_geometry_source = "street_view_far_anchor"
            elif satellite_raw:
                base_geometry = satellite_raw
                base_geometry_source = "satellite"
            else:
                base_geometry = placeholder
        else:
            if street_raw:
                base_geometry = street_raw
                base_geometry_source = "street_view"
            elif satellite_raw:
                base_geometry = satellite_raw
                base_geometry_source = "satellite"
            else:
                base_geometry = placeholder
        if payload.storey_level > 0 and base_geometry_source == "satellite":
            notes.append(
                "Upper-storey framing is using satellite fallback; "
                "forward vista quality may degrade."
            )

        camera_altitude_asl_m = (
            round(elevation_m + payload.derived_altitude_m, 2)
            if elevation_m is not None
            else None
        )
        terrain_note = (
            f"Terrain elevation near site: {elevation_m:.1f}m above sea level."
            if elevation_m is not None
            else "Terrain elevation unavailable."
        )
        viewpoint_note = (
            "For non-ground storeys, frame a forward-facing horizon vista from balcony eye level. "
            "Keep nearby roofline minimal in frame and avoid top-down drone composition. "
            "Use ground and tilt-up street view as primary geometry cues, with far-anchor street "
            "view for depth/occlusion continuity. Use satellite imagery only as emergency topology "
            "fallback. Favor a panoramic left/right feel with natural continuity for panning."
        )

        return VisualContext(
            street_view=street,
            street_view_tilt_up=street_tilt_up,
            street_view_far_anchor=far_anchor_result.image,
            satellite=satellite,
            base_geometry=base_geometry,
            base_geometry_source=base_geometry_source,
            elevation_m=elevation_m,
            camera_altitude_asl_m=camera_altitude_asl_m,
            terrain_note=terrain_note,
            viewpoint_note=viewpoint_note,
            far_anchor_note=far_anchor_result.note,
            far_anchor_distance_m=far_anchor_result.distance_m,
            notes=notes,
        )

    async def fetch_base_geometry(self, payload: PreviewRequest) -> bytes:
        context = await self.fetch_visual_context(payload)
        return context.base_geometry

    async def collect_location_signals(self, lat: float, lng: float) -> tuple[str, list[str]]:
        if self._mock_mode:
            return (
                (
                    f"Mock context around coordinates ({lat:.5f}, {lng:.5f}) with synthetic "
                    "skyline signal."
                ),
                ["Mock Tower", "Mock Marina", "Mock Cultural District"],
            )

        if not self._gmaps:
            return "No Google Maps context available.", []

        reverse_task = asyncio.create_task(asyncio.to_thread(self._reverse_geocode, lat, lng))
        places_task = asyncio.create_task(asyncio.to_thread(self._nearby_places, lat, lng))
        reverse_text, landmarks = await asyncio.gather(
            reverse_task,
            places_task,
            return_exceptions=False,
        )

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
                keyword="skyline landmark viewpoint",
            )
            names = [place.get("name", "") for place in result.get("results", [])]
            cleaned = [name for name in names if name]
            return cleaned[:6]
        except Exception:
            return []

    def _elevation(self, lat: float, lng: float) -> float | None:
        try:
            if not self._gmaps:
                return None
            result = self._gmaps.elevation((lat, lng))
            if not result:
                return None
            elevation = result[0].get("elevation")
            return float(elevation) if isinstance(elevation, (float, int)) else None
        except Exception:
            return None

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
        # Keep the camera mostly forward with a slight upward bias as elevation increases.
        pitch = int(round(2 + (altitude / 500) * 10))
        return max(0, min(18, pitch))

    @staticmethod
    def _storey_to_pitch_up(storey_level: int) -> int:
        # Tilt-up for upper-storey framing while preserving horizon-forward view.
        pitch = int(round(6 + (storey_level / 50) * 18))
        return max(6, min(26, pitch))

    @staticmethod
    def _desired_far_offset_m(altitude_m: float) -> float:
        desired = 80 + (0.9 * altitude_m)
        return max(90.0, min(240.0, desired))

    @classmethod
    def _build_far_anchor_candidates(
        cls,
        lat: float,
        lng: float,
        heading: float,
        desired_offset_m: float,
    ) -> list[tuple[float, float, float, float]]:
        reverse_heading = (heading + 180.0) % 360.0
        candidate_variants = (
            (0.0, 1.0),
            (-25.0, 1.1),
            (25.0, 1.1),
            (0.0, 1.3),
        )
        candidates: list[tuple[float, float, float, float]] = []
        for heading_delta, distance_factor in candidate_variants:
            bearing = (reverse_heading + heading_delta) % 360.0
            distance_m = desired_offset_m * distance_factor
            candidate_lat, candidate_lng = cls._destination_point(lat, lng, bearing, distance_m)
            candidates.append((candidate_lat, candidate_lng, bearing, distance_m))
        return candidates

    @staticmethod
    def _destination_point(
        lat: float,
        lng: float,
        bearing_deg: float,
        distance_m: float,
    ) -> tuple[float, float]:
        angular_distance = distance_m / EARTH_RADIUS_M
        bearing_rad = math.radians(bearing_deg)
        lat_rad = math.radians(lat)
        lng_rad = math.radians(lng)

        sin_lat2 = (math.sin(lat_rad) * math.cos(angular_distance)) + (
            math.cos(lat_rad) * math.sin(angular_distance) * math.cos(bearing_rad)
        )
        lat2_rad = math.asin(max(-1.0, min(1.0, sin_lat2)))
        lng2_rad = lng_rad + math.atan2(
            math.sin(bearing_rad) * math.sin(angular_distance) * math.cos(lat_rad),
            math.cos(angular_distance) - (math.sin(lat_rad) * math.sin(lat2_rad)),
        )
        lng2_rad = ((lng2_rad + (3 * math.pi)) % (2 * math.pi)) - math.pi
        return (math.degrees(lat2_rad), math.degrees(lng2_rad))

    @staticmethod
    def _haversine_distance_m(
        lat1: float,
        lng1: float,
        lat2: float,
        lng2: float,
    ) -> float:
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        hav_a = (math.sin(delta_lat / 2) ** 2) + (
            math.cos(lat1_rad) * math.cos(lat2_rad) * (math.sin(delta_lng / 2) ** 2)
        )
        hav_c = 2 * math.atan2(math.sqrt(hav_a), math.sqrt(max(0.0, 1 - hav_a)))
        return EARTH_RADIUS_M * hav_c

    @staticmethod
    def _bearing_deg(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lng = math.radians(lng2 - lng1)
        y = math.sin(delta_lng) * math.cos(lat2_rad)
        x = (math.cos(lat1_rad) * math.sin(lat2_rad)) - (
            math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lng)
        )
        return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0

    @staticmethod
    def _angular_distance_deg(a_deg: float, b_deg: float) -> float:
        return abs(((a_deg - b_deg + 180.0) % 360.0) - 180.0)

    def _score_far_anchor_candidate(
        self,
        payload: PreviewRequest,
        desired_offset_m: float,
        metadata: dict[str, Any] | None,
    ) -> FarAnchorCandidate | None:
        if not metadata or metadata.get("status") != "OK":
            return None
        location = metadata.get("location")
        if not isinstance(location, dict):
            return None
        pano_lat = location.get("lat")
        pano_lng = location.get("lng")
        if not isinstance(pano_lat, (float, int)) or not isinstance(pano_lng, (float, int)):
            return None

        pano_lat_f = float(pano_lat)
        pano_lng_f = float(pano_lng)
        pano_distance_m = self._haversine_distance_m(
            payload.lat,
            payload.lng,
            pano_lat_f,
            pano_lng_f,
        )
        anchor_to_target_bearing = self._bearing_deg(
            pano_lat_f,
            pano_lng_f,
            payload.lat,
            payload.lng,
        )
        alignment_delta = self._angular_distance_deg(anchor_to_target_bearing, payload.heading)
        alignment = max(0.0, 1.0 - (alignment_delta / 90.0))
        distance_fit = max(
            0.0,
            1.0 - (abs(pano_distance_m - desired_offset_m) / max(1.0, desired_offset_m)),
        )
        score = (0.65 * alignment) + (0.35 * distance_fit)
        return FarAnchorCandidate(
            pano_lat=pano_lat_f,
            pano_lng=pano_lng_f,
            pano_distance_m=pano_distance_m,
            alignment=alignment,
            distance_fit=distance_fit,
            score=score,
        )

    async def _fetch_far_street_view_anchor(self, payload: PreviewRequest) -> FarAnchorResult:
        if not self._settings.far_streetview_enabled or payload.storey_level <= 0:
            return FarAnchorResult(image=b"", note=None, distance_m=None)

        desired_offset_m = self._desired_far_offset_m(payload.derived_altitude_m)
        candidates = self._build_far_anchor_candidates(
            payload.lat,
            payload.lng,
            payload.heading,
            desired_offset_m,
        )

        metadata_tasks = [
            asyncio.create_task(
                self._fetch_street_view_metadata(
                    candidate_lat,
                    candidate_lng,
                    radius_m=self._settings.far_streetview_probe_radius_m,
                )
            )
            for candidate_lat, candidate_lng, _, _ in candidates
        ]
        metadata_results = await asyncio.gather(*metadata_tasks)

        scored: list[FarAnchorCandidate] = []
        for metadata in metadata_results:
            candidate = self._score_far_anchor_candidate(payload, desired_offset_m, metadata)
            if candidate is not None:
                scored.append(candidate)

        if not scored:
            return FarAnchorResult(
                image=b"",
                note="Far Street View anchor unavailable; using near captures only.",
                distance_m=None,
            )

        selected = max(scored, key=lambda candidate: candidate.score)
        far_anchor_image = await self._fetch_street_view(
            payload,
            pitch_override=self._far_anchor_pitch(payload.storey_level),
            fov_override=self._far_anchor_fov(payload.derived_altitude_m),
            location_override=(selected.pano_lat, selected.pano_lng),
        )
        if not far_anchor_image:
            return FarAnchorResult(
                image=b"",
                note=(
                    "Far Street View anchor metadata found but image capture failed; using near "
                    "captures only."
                ),
                distance_m=None,
            )

        return FarAnchorResult(
            image=far_anchor_image,
            note=(
                f"Far Street View anchor selected at {selected.pano_distance_m:.0f}m "
                f"(score {selected.score:.2f})."
            ),
            distance_m=round(selected.pano_distance_m, 1),
        )

    @staticmethod
    def _far_anchor_fov(altitude_m: float) -> int:
        return max(45, min(100, MapsService._altitude_to_fov(altitude_m) + 10))

    @staticmethod
    def _far_anchor_pitch(storey_level: int) -> int:
        return max(4, min(35, MapsService._storey_to_pitch_up(storey_level) - 6))

    async def _fetch_street_view_metadata(
        self,
        lat: float,
        lng: float,
        radius_m: int,
    ) -> dict[str, Any] | None:
        params: dict[str, Any] = {
            "location": f"{lat},{lng}",
            "source": "outdoor",
            "radius": radius_m,
            "key": self._maps_key,
        }
        url = "https://maps.googleapis.com/maps/api/streetview/metadata"
        try:
            async with httpx.AsyncClient(timeout=self._http_timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                return payload
            return None
        except Exception:
            return None

    async def _fetch_street_view(
        self,
        payload: PreviewRequest,
        pitch_override: int | None = None,
        fov_override: int | None = None,
        location_override: tuple[float, float] | None = None,
    ) -> bytes:
        target_lat = payload.lat
        target_lng = payload.lng
        if location_override is not None:
            target_lat, target_lng = location_override
        params: dict[str, Any] = {
            "location": f"{target_lat},{target_lng}",
            "size": "640x360",
            "fov": (
                fov_override
                if fov_override is not None
                else self._altitude_to_fov(payload.derived_altitude_m)
            ),
            "heading": int(round(payload.heading)) % 360,
            "pitch": (
                pitch_override
                if pitch_override is not None
                else self._altitude_to_pitch(payload.derived_altitude_m)
            ),
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
            "zoom": self._altitude_to_zoom(payload.derived_altitude_m),
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
