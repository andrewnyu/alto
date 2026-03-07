from __future__ import annotations

from app.models.preview import LightingProfile, TimeOfDay


class LumenEngine:
    """Maps user-facing time choices to deterministic lighting physics."""

    _MAPPING: dict[TimeOfDay, LightingProfile] = {
        TimeOfDay.SUNRISE: LightingProfile(
            kelvin=2500,
            shadow_length_multiplier=2.7,
            atmospheric_haze=0.38,
            bloom_intensity=0.25,
            iso_grain=0.03,
            prompt_note="2500K low-angle light with morning mist and soft diffusion",
        ),
        TimeOfDay.NOON: LightingProfile(
            kelvin=5600,
            shadow_length_multiplier=0.75,
            atmospheric_haze=0.08,
            bloom_intensity=0.08,
            iso_grain=0.01,
            prompt_note="5600K neutral sun overhead with short, crisp shadows",
        ),
        TimeOfDay.GOLDEN_HOUR: LightingProfile(
            kelvin=3000,
            shadow_length_multiplier=2.3,
            atmospheric_haze=0.22,
            bloom_intensity=0.55,
            iso_grain=0.02,
            prompt_note="3000K intense bloom with amber cast and elongated shadows",
        ),
        TimeOfDay.MIDNIGHT: LightingProfile(
            kelvin=5000,
            shadow_length_multiplier=1.1,
            atmospheric_haze=0.14,
            bloom_intensity=0.12,
            iso_grain=0.34,
            prompt_note="5000K point lights with high-ISO cinematic grain at night",
        ),
    }

    @classmethod
    def profile_for(cls, time_of_day: TimeOfDay) -> LightingProfile:
        return cls._MAPPING[time_of_day]
