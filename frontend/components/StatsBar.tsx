"use client";

import { useEffect, useState } from "react";
import { api, type StatsData } from "@/lib/api";

export function StatsBar() {
  const [stats, setStats] = useState<StatsData | null>(null);

  useEffect(() => {
    api.getStats().then(setStats).catch(() => null);
  }, []);

  if (!stats) return null;

  return (
    <div className="border-t border-gray-100 bg-gray-50 py-2">
      <div className="mx-auto flex max-w-5xl items-center justify-center gap-8 px-4 text-xs text-gray-400">
        <span>
          <strong className="text-gray-600">{stats.total_runs}</strong> advisor sessions run
        </span>
        <span>
          <strong className="text-gray-600">{stats.total_suggestions}</strong> unique suggestions generated
        </span>
        <span>
          <strong className="text-gray-600">{stats.total_votes}</strong> community votes cast
        </span>
      </div>
    </div>
  );
}
