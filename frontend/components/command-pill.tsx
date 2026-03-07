"use client";

import clsx from "clsx";
import { Search, Sparkles } from "lucide-react";

type CommandPillProps = {
  address: string;
  setAddress: (value: string) => void;
  onSearch: () => void;
  onGenerate: () => void;
  isLoading: boolean;
};

export function CommandPill({
  address,
  setAddress,
  onSearch,
  onGenerate,
  isLoading
}: CommandPillProps) {
  return (
    <div className="pointer-events-auto flex w-full max-w-3xl items-center gap-2 rounded-3xl border border-white/40 bg-white/65 p-2 shadow-pill backdrop-blur-xl">
      <button
        type="button"
        onClick={onSearch}
        className="rounded-2xl bg-slate-900/90 p-3 text-white transition hover:bg-slate-950"
        aria-label="Search location"
      >
        <Search className="h-4 w-4" />
      </button>
      <input
        value={address}
        onChange={(event) => setAddress(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            onSearch();
          }
        }}
        placeholder="Search address, district, or coordinates"
        className="h-12 flex-1 rounded-2xl bg-white/70 px-4 text-sm outline-none ring-primary/30 transition focus:ring"
      />
      <button
        type="button"
        onClick={onGenerate}
        disabled={isLoading}
        className={clsx(
          "inline-flex h-12 items-center gap-2 rounded-2xl px-4 text-sm font-semibold transition",
          isLoading
            ? "cursor-not-allowed bg-slate-300 text-slate-600"
            : "bg-primary text-onprimary hover:bg-primary/90"
        )}
      >
        <Sparkles className="h-4 w-4" />
        {isLoading ? "Synthesizing" : "Generate"}
      </button>
    </div>
  );
}
