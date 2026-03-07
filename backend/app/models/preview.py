from __future__ import annotations

from datetime import datetime, timezone
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
    altitude: float = Field(ge=0, le=500, strict=False)
    heading: float = Field(ge=0, le=360, strict=False)
    time_of_day: TimeOfDay = Field(strict=False)


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
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    address: str
    lat: float
    lng: float
    altitude: float
    heading: float
    time_of_day: TimeOfDay
    lighting: LightingProfile
    landmarks: list[str] = Field(default_factory=list)
    pitch: str = Field(min_length=3)
    base_geometry_image: str = Field(min_length=30)
    rendered_image: str = Field(min_length=30)
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
