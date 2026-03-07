"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { GoogleMap, MarkerF, useJsApiLoader } from "@react-google-maps/api";
import { motion } from "framer-motion";

import {
  createPreview,
  fetchHealthStatus,
  geocodeAddress as geocodeAddressApi
} from "@/lib/api";
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

function storeyToZoom(storeyLevel: number): number {
  const zoom = 20 - Math.round((storeyLevel / 50) * 5);
  return Math.max(15, Math.min(20, zoom));
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
  const [selectedPin, setSelectedPin] = useState(DEFAULT_CENTER);
  const [storeyLevel, setStoreyLevel] = useState(12);
  const [heading, setHeading] = useState(150);
  const [timeOfDay, setTimeOfDay] = useState<TimeOfDay>("GoldenHour");

  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSynthesizing, setIsSynthesizing] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [nanoBananaStatus, setNanoBananaStatus] = useState<
    "checking" | "available" | "unavailable" | "unknown"
  >("checking");
  const [nanoBananaModel, setNanoBananaModel] = useState<string>("nano-banana-2");

  const mapRef = useRef<MapRef>(null);
  const missingMapsKey = mapsBrowserApiKey.trim().length === 0;
  const zoom = useMemo(() => storeyToZoom(storeyLevel), [storeyLevel]);

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

  useEffect(() => {
    let active = true;
    setNanoBananaStatus("checking");

    const loadHealth = async () => {
      try {
        const health = await fetchHealthStatus(apiBaseUrl);
        if (!active) {
          return;
        }
        if (typeof health.nano_banana_model === "string" && health.nano_banana_model.trim()) {
          setNanoBananaModel(health.nano_banana_model);
        }
        if (typeof health.nano_banana_available === "boolean") {
          setNanoBananaStatus(health.nano_banana_available ? "available" : "unavailable");
          return;
        }
        setNanoBananaStatus("unknown");
      } catch {
        if (!active) {
          return;
        }
        setNanoBananaStatus("unknown");
      }
    };

    void loadHealth();
    return () => {
      active = false;
    };
  }, [apiBaseUrl]);

  const applyCenter = useCallback((lat: number, lng: number) => {
    const nextCenter = { lat, lng };
    setCenter(nextCenter);
    setSelectedPin(nextCenter);
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
        storey_level: storeyLevel,
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
  }, [address, apiBaseUrl, center.lat, center.lng, heading, storeyLevel, timeOfDay]);

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
                applyCenter(lat, lng);
                setAddress(`${lat.toFixed(6)}, ${lng.toFixed(6)}`);
                setError(null);
              }
            }}
          >
            <MarkerF position={selectedPin} />
          </GoogleMap>
        ) : (
          <div className="h-full w-full animate-pulse bg-slate-200" />
        )}
      </div>

      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_72%_18%,rgba(255,198,120,0.15),rgba(0,0,0,0)_35%)]" />

      {isSynthesizing ? (
        <motion.div
          className="absolute inset-0 z-[60] flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-md"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.div
            className="w-full max-w-lg rounded-3xl border border-white/20 bg-slate-900/78 p-6 text-white shadow-2xl"
            initial={{ y: 16, opacity: 0, scale: 0.98 }}
            animate={{ y: 0, opacity: 1, scale: 1 }}
            transition={{ type: "spring", stiffness: 200, damping: 20 }}
          >
            <p className="text-[11px] uppercase tracking-[0.2em] text-cyan-200">
              {nanoBananaStatus === "available" ? "Nano Banana Active" : "Image Generation"}
            </p>
            <h3 className="mt-2 text-2xl font-semibold tracking-tight">
              Generating Panoramic Vista
            </h3>
            <p className="mt-2 text-sm text-slate-200">
              Synthesizing a beautiful forward-facing view from street-level guides at{" "}
              {storeyLevel === 0 ? "Ground" : `L${storeyLevel}`}.
            </p>
            <p className="mt-1 text-xs text-slate-300">
              Target pin: {selectedPin.lat.toFixed(6)}, {selectedPin.lng.toFixed(6)}
            </p>
            <div className="mt-5 h-2 overflow-hidden rounded-full bg-slate-700/70">
              <motion.div
                className="h-full w-1/3 bg-gradient-to-r from-cyan-300 via-sky-300 to-indigo-300"
                initial={{ x: "-100%" }}
                animate={{ x: "320%" }}
                transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
              />
            </div>
            <div className="mt-4 space-y-1 text-xs text-slate-300">
              <p>1. Fetching Street View anchors and orientation cues</p>
              <p>2. Inferring elevated horizon composition from storey height</p>
              <p>3. Rendering panoramic beauty pass with Nano Banana</p>
            </div>
          </motion.div>
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
      <div className="pointer-events-none absolute left-0 right-0 top-24 z-40 flex justify-center px-4">
        <div className="rounded-full border border-white/45 bg-white/70 px-4 py-2 text-[11px] font-medium tracking-[0.08em] text-slate-700 backdrop-blur-xl">
          Pinned target: {selectedPin.lat.toFixed(6)}, {selectedPin.lng.toFixed(6)}
        </div>
      </div>
      <div className="pointer-events-none absolute left-4 top-28 z-40">
        <div
          className={`rounded-full border px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.12em] backdrop-blur-xl ${
            nanoBananaStatus === "checking"
              ? "border-white/45 bg-white/70 text-slate-700"
              : nanoBananaStatus === "available"
                ? "border-emerald-200 bg-emerald-50/90 text-emerald-800"
                : nanoBananaStatus === "unavailable"
                  ? "border-amber-200 bg-amber-50/90 text-amber-900"
                  : "border-slate-300 bg-slate-100/90 text-slate-700"
          }`}
        >
          {nanoBananaStatus === "checking"
            ? "Nano Banana status: Checking"
            : nanoBananaStatus === "available"
              ? `Nano Banana: Available (${nanoBananaModel})`
              : nanoBananaStatus === "unavailable"
                ? "Nano Banana: Unavailable (using fallback)"
                : "Nano Banana: Unknown (backend health schema outdated)"}
        </div>
      </div>

      <div className="pointer-events-none absolute right-4 top-28 z-40">
        <VantageSidebar
          storeyLevel={storeyLevel}
          setStoreyLevel={setStoreyLevel}
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
