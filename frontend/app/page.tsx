import { HorizonInterface } from "@/components/horizon-interface";

export default function HomePage() {
  const mapsBrowserApiKey = process.env.GOOGLE_MAPS_BROWSER_API_KEY ?? "";
  const apiBaseUrl = (process.env.PUBLIC_BASE_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

  return <HorizonInterface mapsBrowserApiKey={mapsBrowserApiKey} apiBaseUrl={apiBaseUrl} />;
}
