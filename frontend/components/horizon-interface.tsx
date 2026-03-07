"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { GoogleMap, useJsApiLoader } from "@react-google-maps/api";
import { motion } from "framer-motion";

import { createPreview, geocodeAddress as geocodeAddressApi } from "@/lib/api";
import { PreviewResponse, TimeOfDay } from "@/lib/types";
import { CommandPill } from "@/components/command-pill";
import { SynthesisModal } from "@/components/synthesis-modal";
import { VantageSidebar } from "@/components/vantage-sidebar";

const MAP_STYLE = {
  width: "100%",
  height: "100%"
};

const DEFAULT_CENTER = { lat: 37.79061, lng: -122.39695 };

type MapRef = google.maps.Map | null;

function altitudeToZoom(altitude: number): number {
  const zoom = 20 - Math.round((altitude / 500) * 6);
  return Math.max(14, Math.min(20, zoom));
}

function parseCoordinateQuery(query: string): { lat: number; lng: number } | null {
  const trimmed = query.trim();
  const match = trimmed.match(
    /^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$/
  );
  if (!match) {
    return null;
  }
  const lat = Number(match[1]);
  const lng = Number(match[2]);
  if (
    Number.isNaN(lat) ||
    Number.isNaN(lng) ||
    lat < -90 ||
    lat > 90 ||
    lng < -180 ||
    lng > 180
  ) {
    return null;
  }
  return { lat, lng };
}

type HorizonInterfaceProps = {
  mapsBrowserApiKey: string;
  apiBaseUrl: string;
};

export function HorizonInterface({ mapsBrowserApiKey, apiBaseUrl }: HorizonInterfaceProps) {
  const [address, setAddress] = useState("181 Fremont St, San Francisco, CA");
  const [center, setCenter] = useState(DEFAULT_CENTER);
  const [altitude, setAltitude] = useState(120);
  const [heading, setHeading] = useState(150);
  const [timeOfDay, setTimeOfDay] = useState<TimeOfDay>("GoldenHour");

  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSynthesizing, setIsSynthesizing] = useState(false);
  const [showModal, setShowModal] = useState(false);

  const mapRef = useRef<MapRef>(null);
  const missingMapsKey = mapsBrowserApiKey.trim().length === 0;
  const zoom = useMemo(() => altitudeToZoom(altitude), [altitude]);

  const { isLoaded, loadError } = useJsApiLoader({
    googleMapsApiKey: mapsBrowserApiKey,
    libraries: ["places"]
  });

  const mapOptions = useMemo<google.maps.MapOptions>(
    () => ({
      disableDefaultUI: true,
      clickableIcons: false,
      tilt: 67.5,
      heading,
      zoom,
      keyboardShortcuts: false,
      gestureHandling: "greedy"
    }),
    [heading, zoom]
  );

  useEffect(() => {
    if (!mapRef.current) {
      return;
    }
    mapRef.current.setHeading(heading);
    mapRef.current.setZoom(zoom);
    mapRef.current.setTilt(67.5);
  }, [heading, zoom]);

  const applyCenter = useCallback((lat: number, lng: number) => {
    const nextCenter = { lat, lng };
    setCenter(nextCenter);
    if (mapRef.current) {
      mapRef.current.panTo(nextCenter);
    }
  }, []);

  const findPlaceViaPlacesApi = useCallback(
    async (query: string): Promise<boolean> => {
      if (!window.google?.maps || !mapRef.current) {
        return false;
      }

      const service = new window.google.maps.places.PlacesService(mapRef.current);
      return await new Promise<boolean>((resolve) => {
        service.findPlaceFromQuery(
          {
            query,
            fields: ["name", "formatted_address", "geometry"]
          },
          (results, status) => {
            if (
              status !== window.google.maps.places.PlacesServiceStatus.OK ||
              !results?.length ||
              !results[0].geometry?.location
            ) {
              resolve(false);
              return;
            }

            const first = results[0];
            const geometry = first.geometry;
            const loc = geometry?.location;
            if (!loc) {
              resolve(false);
              return;
            }
            applyCenter(loc.lat(), loc.lng());
            setAddress(first.formatted_address || first.name || query);
            setError(null);
            resolve(true);
          }
        );
      });
    },
    [applyCenter]
  );

  const geocodeWithBackendFallback = useCallback(
    async (reason?: string) => {
      const trimmedAddress = address.trim();
      if (!trimmedAddress) {
        setError("Enter an address first.");
        return;
      }

      try {
        const result = await geocodeAddressApi(trimmedAddress, apiBaseUrl);
        applyCenter(result.lat, result.lng);
        setAddress(result.formatted_address);
        setError(null);
      } catch (lookupError) {
        const detail = lookupError instanceof Error ? lookupError.message : "Unknown geocode error.";
        const reasonText = reason ? ` (${reason})` : "";
        setError(`Address lookup failed${reasonText}. ${detail}`);
      }
    },
    [address, apiBaseUrl, applyCenter]
  );

  const geocodeAddress = useCallback(async () => {
    const trimmedAddress = address.trim();
    if (!trimmedAddress) {
      setError("Enter an address first.");
      return;
    }

    const coordinateQuery = parseCoordinateQuery(trimmedAddress);
    if (coordinateQuery) {
      applyCenter(coordinateQuery.lat, coordinateQuery.lng);
      setError(null);
      return;
    }

    if (!window.google?.maps) {
      await geocodeWithBackendFallback("google maps not loaded");
      return;
    }

    const geocoder = new window.google.maps.Geocoder();
    geocoder.geocode({ address: trimmedAddress }, async (results, status) => {
      if (status === "OK" && results?.length) {
        const location = results[0].geometry.location;
        applyCenter(location.lat(), location.lng());
        setAddress(results[0].formatted_address ?? trimmedAddress);
        setError(null);
        return;
      }

      const resolvedByPlaces = await findPlaceViaPlacesApi(trimmedAddress);
      if (resolvedByPlaces) {
        return;
      }

      await geocodeWithBackendFallback(status);
    });
  }, [address, applyCenter, findPlaceViaPlacesApi, geocodeWithBackendFallback]);

  const runSynthesis = useCallback(async () => {
    setError(null);
    setIsSynthesizing(true);

    try {
      const generated = await createPreview({
        address,
        lat: center.lat,
        lng: center.lng,
        altitude,
        heading,
        time_of_day: timeOfDay
      }, apiBaseUrl);

      setPreview(generated);
      setShowModal(true);
    } catch (synthesisError) {
      setError(
        synthesisError instanceof Error
          ? synthesisError.message
          : "Synthesis failed. Validate API keys and backend availability."
      );
    } finally {
      setIsSynthesizing(false);
    }
  }, [address, altitude, apiBaseUrl, center.lat, center.lng, heading, timeOfDay]);

  return (
    <main className="relative h-screen w-screen">
      <div className="absolute inset-0">
        {missingMapsKey ? (
          <div className="flex h-full items-center justify-center bg-slate-100 text-slate-700">
            Missing GOOGLE_MAPS_BROWSER_API_KEY.
          </div>
        ) : loadError ? (
          <div className="flex h-full items-center justify-center bg-slate-100 text-slate-700">
            Failed to load Google Maps API.
          </div>
        ) : isLoaded ? (
          <GoogleMap
            mapContainerStyle={MAP_STYLE}
            center={center}
            zoom={zoom}
            options={mapOptions}
            onLoad={(map) => {
              mapRef.current = map;
              map.setTilt(67.5);
              map.setHeading(heading);
              map.setZoom(zoom);
            }}
            onClick={(event) => {
              const lat = event.latLng?.lat();
              const lng = event.latLng?.lng();
              if (typeof lat === "number" && typeof lng === "number") {
                setCenter({ lat, lng });
              }
            }}
          />
        ) : (
          <div className="h-full w-full animate-pulse bg-slate-200" />
        )}
      </div>

      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_72%_18%,rgba(255,198,120,0.15),rgba(0,0,0,0)_35%)]" />

      {isSynthesizing ? (
        <motion.div
          className="pointer-events-none absolute inset-0 z-30 overflow-hidden"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.div
            className="absolute left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-cyan-200 to-transparent shadow-[0_0_26px_rgba(95,205,255,0.9)]"
            initial={{ top: "-4%" }}
            animate={{ top: "108%" }}
            transition={{ duration: 1.2, repeat: Infinity, ease: "linear" }}
          />
        </motion.div>
      ) : null}

      <div className="pointer-events-none absolute left-0 right-0 top-6 z-40 flex justify-center px-4">
        <CommandPill
          address={address}
          setAddress={setAddress}
          onSearch={geocodeAddress}
          onGenerate={runSynthesis}
          isLoading={isSynthesizing}
        />
      </div>

      <div className="pointer-events-none absolute right-4 top-28 z-40">
        <VantageSidebar
          altitude={altitude}
          setAltitude={setAltitude}
          heading={heading}
          setHeading={setHeading}
          timeOfDay={timeOfDay}
          setTimeOfDay={setTimeOfDay}
        />
      </div>

      {error ? (
        <div className="absolute bottom-4 left-1/2 z-40 -translate-x-1/2 rounded-2xl bg-red-600/90 px-4 py-2 text-sm text-white shadow-lg">
          {error}
        </div>
      ) : null}

      <SynthesisModal preview={preview} open={showModal} onClose={() => setShowModal(false)} />
    </main>
  );
}
