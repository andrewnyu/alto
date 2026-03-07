from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, computed_field


class TimeOfDay(StrEnum):
    SUNRISE = "Sunrise"
    NOON = "Noon"
    GOLDEN_HOUR = "GoldenHour"
    MIDNIGHT = "Midnight"


class PreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    address: str = Field(min_length=3, max_length=300)
    lat: float = Field(ge=-90, le=90, strict=False)
    lng: float = Field(ge=-180, le=180, strict=False)
    storey_level: int = Field(default=0, ge=0, le=50, strict=False)
    altitude: float | None = Field(default=None, ge=0, le=500, strict=False)
    heading: float = Field(ge=0, le=360, strict=False)
    time_of_day: TimeOfDay = Field(strict=False)

    @computed_field(return_type=float)
    @property
    def derived_altitude_m(self) -> float:
        if self.altitude is not None:
            return self.altitude
        # Approximate 3.2m per storey.
        return round(self.storey_level * 3.2, 1)


class LightingProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    kelvin: int = Field(ge=1000, le=10000)
    shadow_length_multiplier: float = Field(ge=0.1, le=4.0)
    atmospheric_haze: float = Field(ge=0.0, le=1.0)
    bloom_intensity: float = Field(ge=0.0, le=2.0)
    iso_grain: float = Field(ge=0.0, le=1.0)
    prompt_note: str = Field(min_length=5, max_length=220)


class PreviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    request_id: UUID = Field(default_factory=uuid4)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    address: str
    lat: float
    lng: float
    storey_level: int = Field(ge=0, le=50)
    altitude: float
    heading: float
    elevation_m: float | None = None
    camera_altitude_asl_m: float | None = None
    time_of_day: TimeOfDay
    lighting: LightingProfile
    landmarks: list[str] = Field(default_factory=list)
    context_notes: list[str] = Field(default_factory=list)
    pitch: str = Field(min_length=3)
    street_view_image: str = Field(min_length=30)
    street_view_tilt_up_image: str = Field(min_length=30)
    satellite_image: str = Field(min_length=30)
    base_geometry_image: str = Field(min_length=30)
    base_geometry_source: str = Field(min_length=3, max_length=40)
    rendered_image: str = Field(min_length=30)
    render_source: str = Field(min_length=3, max_length=60)
    render_is_stock_fallback: bool = False
    render_fallback_reason: str | None = Field(default=None, max_length=260)
    render_model: str = Field(min_length=3, max_length=80)
    render_reference_count: int = Field(ge=0, le=12)
    latency_ms: int = Field(ge=0)

    @computed_field(return_type=str)
    @property
    def generated_at_iso(self) -> str:
        return self.generated_at.isoformat()


class GeocodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    address: str = Field(min_length=3, max_length=300)


class GeocodeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    address: str = Field(min_length=3, max_length=300)
    formatted_address: str = Field(min_length=3, max_length=300)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    provider: str = Field(min_length=3, max_length=40)
