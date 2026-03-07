export type TimeOfDay = "Sunrise" | "Noon" | "GoldenHour" | "Midnight";

export interface PreviewRequest {
  address: string;
  lat: number;
  lng: number;
  altitude: number;
  heading: number;
  time_of_day: TimeOfDay;
}

export interface LightingProfile {
  kelvin: number;
  shadow_length_multiplier: number;
  atmospheric_haze: number;
  bloom_intensity: number;
  iso_grain: number;
  prompt_note: string;
}

export interface PreviewResponse {
  request_id: string;
  generated_at: string;
  generated_at_iso: string;
  address: string;
  lat: number;
  lng: number;
  altitude: number;
  heading: number;
  time_of_day: TimeOfDay;
  lighting: LightingProfile;
  landmarks: string[];
  pitch: string;
  base_geometry_image: string;
  rendered_image: string;
  latency_ms: number;
}

export interface GeocodeResponse {
  address: string;
  formatted_address: string;
  lat: number;
  lng: number;
  provider: string;
}
