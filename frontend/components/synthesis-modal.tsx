"use client";

import { AnimatePresence, motion } from "framer-motion";

import { PreviewResponse } from "@/lib/types";

type SynthesisModalProps = {
  preview: PreviewResponse | null;
  open: boolean;
  onClose: () => void;
};

export function SynthesisModal({ preview, open, onClose }: SynthesisModalProps) {
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
              <div className="bg-slate-100">
                <img
                  src={preview.rendered_image}
                  alt="ALTO generated luxury render"
                  className="h-full w-full object-cover"
                />
              </div>
              <div className="space-y-5 p-6">
                <div>
                  <h3 className="font-display text-xl tracking-tight text-slate-950">ALTO Synthesis</h3>
                  <p className="mt-1 text-sm text-slate-600">{preview.address}</p>
                </div>
                <blockquote className="rounded-2xl border border-slate-200 bg-white/65 p-4 text-sm leading-relaxed text-slate-800">
                  {preview.pitch}
                </blockquote>
                <div className="space-y-2 text-xs uppercase tracking-[0.14em] text-slate-600">
                  <p>Time: {preview.time_of_day}</p>
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
              </div>
            </div>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
