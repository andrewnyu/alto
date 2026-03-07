"use client";

import clsx from "clsx";
import { Compass } from "lucide-react";

import { TimeOfDay } from "@/lib/types";

const TIME_OPTIONS: Array<{ value: TimeOfDay; label: string; icon: string }> = [
  { value: "Sunrise", label: "Sunrise", icon: "🌅" },
  { value: "Noon", label: "Noon", icon: "☀️" },
  { value: "GoldenHour", label: "Golden", icon: "🌇" },
  { value: "Midnight", label: "Midnight", icon: "🌙" }
];

type VantageSidebarProps = {
  storeyLevel: number;
  setStoreyLevel: (value: number) => void;
  heading: number;
  setHeading: (value: number) => void;
  timeOfDay: TimeOfDay;
  setTimeOfDay: (value: TimeOfDay) => void;
};

export function VantageSidebar({
  storeyLevel,
  setStoreyLevel,
  heading,
  setHeading,
  timeOfDay,
  setTimeOfDay
}: VantageSidebarProps) {
  return (
    <aside className="pointer-events-auto w-80 rounded-3xl border border-white/35 bg-white/45 p-5 shadow-glass backdrop-blur-xl">
      <div className="mb-5 flex items-center gap-2">
        <Compass className="h-4 w-4 text-slate-700" />
        <h2 className="font-display text-sm uppercase tracking-[0.24em] text-slate-700">Vantage</h2>
      </div>

      <section className="space-y-2">
        <div className="flex items-center justify-between">
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-slate-600">Storey</p>
          <p className="text-sm font-semibold text-slate-900">
            {storeyLevel === 0 ? "Ground" : `L${storeyLevel}`}
          </p>
        </div>
        <input
          type="range"
          min={0}
          max={50}
          step={1}
          value={storeyLevel}
          onChange={(event) => setStoreyLevel(Number(event.target.value))}
          className="h-2 w-full cursor-pointer appearance-none rounded-full bg-slate-300 accent-primary"
        />
      </section>

      <section className="mt-6 space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-slate-600">Heading</p>
          <p className="text-sm font-semibold text-slate-900">{Math.round(heading)}°</p>
        </div>
        <div className="relative mx-auto flex h-28 w-28 items-center justify-center rounded-full border border-white/40 bg-white/70">
          <div className="absolute h-20 w-20 rounded-full border border-slate-200" />
          <div
            className="absolute h-12 w-[2px] origin-bottom bg-primary"
            style={{ transform: `rotate(${heading}deg) translateY(-18px)` }}
          />
          <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">N</span>
        </div>
        <input
          type="range"
          min={0}
          max={360}
          step={1}
          value={heading}
          onChange={(event) => setHeading(Number(event.target.value))}
          className="h-2 w-full cursor-pointer appearance-none rounded-full bg-slate-300 accent-primary"
        />
      </section>

      <section className="mt-6">
        <p className="mb-2 text-xs font-medium uppercase tracking-[0.16em] text-slate-600">Time of Day</p>
        <div className="grid grid-cols-4 gap-2">
          {TIME_OPTIONS.map((option) => (
            <button
              type="button"
              key={option.value}
              onClick={() => setTimeOfDay(option.value)}
              className={clsx(
                "rounded-2xl px-2 py-3 text-center transition",
                timeOfDay === option.value
                  ? "bg-primary text-white"
                  : "bg-white/70 text-slate-700 hover:bg-white"
              )}
              title={option.label}
            >
              <div className="text-base leading-none">{option.icon}</div>
              <div className="mt-1 text-[10px] font-semibold uppercase tracking-[0.12em]">{option.label}</div>
            </button>
          ))}
        </div>
      </section>
    </aside>
  );
}
