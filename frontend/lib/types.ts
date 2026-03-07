export type TimeOfDay = "Sunrise" | "Noon" | "GoldenHour" | "Midnight";

export interface PreviewRequest {
  address: string;
  lat: number;
  lng: number;
  storey_level: number;
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
  storey_level: number;
  altitude: number;
  heading: number;
  elevation_m: number | null;
  camera_altitude_asl_m: number | null;
  time_of_day: TimeOfDay;
  lighting: LightingProfile;
  landmarks: string[];
  context_notes: string[];
  pitch: string;
  street_view_image: string;
  street_view_tilt_up_image: string;
  satellite_image: string;
  base_geometry_image: string;
  base_geometry_source: string;
  rendered_image: string;
  render_source: string;
  render_is_stock_fallback: boolean;
  render_fallback_reason: string | null;
  render_model: string;
  render_reference_count: number;
  latency_ms: number;
}

export interface GeocodeResponse {
  address: string;
  formatted_address: string;
  lat: number;
  lng: number;
  provider: string;
}

export interface HealthStatusResponse {
  status: string;
  nano_banana_available?: boolean;
  nano_banana_model?: string;
  mock_mode?: boolean;
}
