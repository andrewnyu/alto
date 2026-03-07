"use client";

import { type PointerEvent, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

import { PreviewResponse } from "@/lib/types";

type SynthesisModalProps = {
  preview: PreviewResponse | null;
  open: boolean;
  onClose: () => void;
};

const YAW_MIN = -90;
const YAW_MAX = 90;
const PANORAMA_WIDTH_PERCENT = 240;
const PAN_TRANSLATE_LIMIT =
  ((PANORAMA_WIDTH_PERCENT - 100) / 2) / (PANORAMA_WIDTH_PERCENT / 100);
const DRAG_DEGREES_PER_PIXEL = 0.25;

function clampYaw(value: number): number {
  return Math.max(YAW_MIN, Math.min(YAW_MAX, value));
}

export function SynthesisModal({ preview, open, onClose }: SynthesisModalProps) {
  const [yawDegrees, setYawDegrees] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const dragStartRef = useRef<{ x: number; yaw: number } | null>(null);

  useEffect(() => {
    if (!open || !preview) {
      setYawDegrees(0);
      setIsDragging(false);
      dragStartRef.current = null;
      return;
    }
    setYawDegrees(0);
  }, [open, preview]);

  // Neutral yaw (0deg) is centered. +/-90deg reaches each panorama edge.
  const panOffset = -PAN_TRANSLATE_LIMIT - (yawDegrees / YAW_MAX) * PAN_TRANSLATE_LIMIT;

  const handlePointerDown = (event: PointerEvent<HTMLDivElement>) => {
    dragStartRef.current = { x: event.clientX, yaw: yawDegrees };
    setIsDragging(true);
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const handlePointerMove = (event: PointerEvent<HTMLDivElement>) => {
    if (!dragStartRef.current) {
      return;
    }
    const deltaX = event.clientX - dragStartRef.current.x;
    setYawDegrees(clampYaw(dragStartRef.current.yaw - deltaX * DRAG_DEGREES_PER_PIXEL));
  };

  const handlePointerUp = (event: PointerEvent<HTMLDivElement>) => {
    dragStartRef.current = null;
    setIsDragging(false);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  };

  return (
    <AnimatePresence>
      {open && preview ? (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/55 p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.div
            className="max-h-[92vh] w-full max-w-6xl overflow-hidden rounded-3xl border border-white/25 bg-white/80 shadow-glass backdrop-blur-xl"
            initial={{ y: 28, opacity: 0, scale: 0.98 }}
            animate={{ y: 0, opacity: 1, scale: 1 }}
            exit={{ y: 20, opacity: 0, scale: 0.97 }}
            transition={{ type: "spring", stiffness: 180, damping: 20 }}
            onClick={(event) => event.stopPropagation()}
          >
            <div className="grid gap-0 lg:grid-cols-[2fr_1fr]">
              <div className="flex h-full flex-col bg-slate-100">
                <div
                  className={`relative flex-1 overflow-hidden touch-none ${
                    isDragging ? "cursor-grabbing" : "cursor-grab"
                  }`}
                  onPointerDown={handlePointerDown}
                  onPointerMove={handlePointerMove}
                  onPointerUp={handlePointerUp}
                  onPointerCancel={handlePointerUp}
                >
                  <img
                    src={preview.rendered_image}
                    alt="ALTO generated luxury render"
                    className="h-full max-w-none object-cover"
                    style={{
                      width: `${PANORAMA_WIDTH_PERCENT}%`,
                      transform: `translateX(${panOffset}%)`,
                    }}
                    draggable={false}
                  />
                  <div className="pointer-events-none absolute left-3 top-3 rounded-full bg-black/40 px-3 py-1 text-[11px] uppercase tracking-[0.14em] text-white">
                    180° Panorama
                  </div>
                </div>
                <div className="space-y-2 border-t border-slate-200/70 bg-white/85 px-4 py-3">
                  <div className="flex items-center justify-between text-[11px] uppercase tracking-[0.14em] text-slate-600">
                    <span>Yaw ({Math.round(yawDegrees)}°)</span>
                    <button
                      type="button"
                      className="rounded-md border border-slate-300 px-2 py-0.5 text-[10px] text-slate-700 transition hover:bg-slate-100"
                      onClick={() => setYawDegrees(0)}
                    >
                      Center
                    </button>
                  </div>
                  <input
                    type="range"
                    min={YAW_MIN}
                    max={YAW_MAX}
                    step={1}
                    value={yawDegrees}
                    onChange={(event) => setYawDegrees(clampYaw(Number(event.target.value)))}
                    className="w-full accent-slate-800"
                    aria-label="Rotate rendered panorama horizontally"
                  />
                  <p className="text-[11px] text-slate-500">
                    Drag the view or use the slider for a 180-degree panoramic sweep.
                  </p>
                </div>
              </div>
              <div className="space-y-5 p-6">
                <div>
                  <h3 className="font-display text-xl tracking-tight text-slate-950">ALTO Synthesis</h3>
                  <p className="mt-1 text-sm text-slate-600">{preview.address}</p>
                </div>
                {preview.render_is_stock_fallback ? (
                  <div className="rounded-2xl border border-red-300 bg-red-50/95 p-3 text-xs text-red-900">
                    <p className="font-semibold uppercase tracking-[0.12em]">
                      Stock Fallback Detected
                    </p>
                    <p className="mt-1">
                      {preview.render_fallback_reason ||
                        "Rendered image appears to be a Street View/base fallback instead of a synthesized vista."}
                    </p>
                  </div>
                ) : (
                  <div className="rounded-2xl border border-emerald-200 bg-emerald-50/90 p-3 text-xs text-emerald-900">
                    <p className="font-semibold uppercase tracking-[0.12em]">
                      Nano Banana Synthesis Active
                    </p>
                    <p className="mt-1">
                      Model: {preview.render_model}. Reference images used:{" "}
                      {preview.render_reference_count}.
                    </p>
                  </div>
                )}
                <blockquote className="rounded-2xl border border-slate-200 bg-white/65 p-4 text-sm leading-relaxed text-slate-800">
                  {preview.pitch}
                </blockquote>
                <div className="space-y-2 text-xs uppercase tracking-[0.14em] text-slate-600">
                  <p>Time: {preview.time_of_day}</p>
                  <p>Storey: {preview.storey_level === 0 ? "Ground" : `L${preview.storey_level}`}</p>
                  <p>Altitude: {preview.altitude.toFixed(1)}m</p>
                  <p>
                    Elevation:{" "}
                    {typeof preview.elevation_m === "number"
                      ? `${preview.elevation_m.toFixed(1)}m`
                      : "N/A"}
                  </p>
                  <p>
                    Camera ASL:{" "}
                    {typeof preview.camera_altitude_asl_m === "number"
                      ? `${preview.camera_altitude_asl_m.toFixed(1)}m`
                      : "N/A"}
                  </p>
                  <p>Base Source: {preview.base_geometry_source}</p>
                  <p>Render Source: {preview.render_source}</p>
                  <p>Kelvin: {preview.lighting.kelvin}K</p>
                  <p>Latency: {preview.latency_ms}ms</p>
                </div>
                {preview.landmarks.length ? (
                  <div className="flex flex-wrap gap-2">
                    {preview.landmarks.slice(0, 5).map((landmark) => (
                      <span
                        key={landmark}
                        className="rounded-full border border-slate-200 bg-white/80 px-3 py-1 text-xs text-slate-700"
                      >
                        {landmark}
                      </span>
                    ))}
                  </div>
                ) : null}
                {preview.context_notes.length ? (
                  <div className="rounded-2xl border border-amber-200 bg-amber-50/90 p-3 text-xs text-amber-900">
                    {preview.context_notes.map((note) => (
                      <p key={note}>{note}</p>
                    ))}
                  </div>
                ) : null}
              </div>
            </div>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
