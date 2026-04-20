"use client";

interface DemoBannerProps {
  onDismiss: () => void;
}

export function DemoBanner({ onDismiss }: DemoBannerProps) {
  return (
    <div className="w-full bg-[#00ff87] text-[#37003c]">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-2 text-sm font-semibold">
        <span>
          🎮 <strong>Demo mode</strong> — pre-loaded with Ferdinand&apos;s team (entry 860655, league 130708).
          The simulation runs automatically so the professor sees real output on landing.
        </span>
        <button
          onClick={onDismiss}
          className="ml-4 shrink-0 rounded px-2 py-0.5 text-xs hover:bg-[#37003c] hover:text-[#00ff87] transition-colors"
        >
          Use my team →
        </button>
      </div>
    </div>
  );
}
