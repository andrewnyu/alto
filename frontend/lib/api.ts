import {
  GeocodeResponse,
  HealthStatusResponse,
  PreviewRequest,
  PreviewResponse
} from "@/lib/types";

export async function createPreview(
  payload: PreviewRequest,
  apiBaseUrl: string
): Promise<PreviewResponse> {
  const baseUrl = apiBaseUrl.replace(/\/$/, "");
  const response = await fetch(`${baseUrl}/api/v1/preview`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    cache: "no-store",
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || "Failed to generate ALTO preview");
  }

  return (await response.json()) as PreviewResponse;
}

export async function geocodeAddress(
  address: string,
  apiBaseUrl: string
): Promise<GeocodeResponse> {
  const baseUrl = apiBaseUrl.replace(/\/$/, "");
  const response = await fetch(`${baseUrl}/api/v1/geocode`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    cache: "no-store",
    body: JSON.stringify({ address })
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || "Failed to geocode address");
  }

  return (await response.json()) as GeocodeResponse;
}

export async function fetchHealthStatus(apiBaseUrl: string): Promise<HealthStatusResponse> {
  const baseUrl = apiBaseUrl.replace(/\/$/, "");
  const response = await fetch(`${baseUrl}/healthz`, {
    method: "GET",
    cache: "no-store"
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || "Failed to fetch health status");
  }

  return (await response.json()) as HealthStatusResponse;
}
