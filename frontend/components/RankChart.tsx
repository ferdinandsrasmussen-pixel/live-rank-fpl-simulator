"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

interface RankChartProps {
  data: { rank: number; count: number }[];
  rankP10: number;
  rankP50: number;
  rankP90: number;
}

const CustomTooltip = ({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { value: number; payload: { rank: number } }[];
}) => {
  if (active && payload?.length) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white px-3 py-2 shadow text-sm">
        <p className="font-semibold">Rank {payload[0].payload.rank}</p>
        <p className="text-gray-600">{payload[0].value} simulations</p>
      </div>
    );
  }
  return null;
};

export function RankChart({ data, rankP10, rankP50, rankP90 }: RankChartProps) {
  // Opacity scales with proximity to median — gives a natural "bell" feel
  const maxCount = Math.max(...data.map((d) => d.count), 1);

  return (
    <div className="w-full">
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data} margin={{ top: 16, right: 16, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
          <XAxis
            dataKey="rank"
            tick={{ fontSize: 12, fill: "#6b7280" }}
            label={{ value: "Mini-league rank", position: "insideBottom", offset: -2, fontSize: 12, fill: "#6b7280" }}
          />
          <YAxis
            tick={{ fontSize: 12, fill: "#6b7280" }}
            label={{ value: "Simulations", angle: -90, position: "insideLeft", fontSize: 12, fill: "#6b7280" }}
          />
          <Tooltip content={<CustomTooltip />} />

          {/* P10 — best realistic outcome */}
          <ReferenceLine
            x={rankP10}
            stroke="#16a34a"
            strokeWidth={2}
            strokeDasharray="4 2"
            label={{ value: `P10 (${rankP10})`, fill: "#16a34a", fontSize: 11, position: "top" }}
          />
          {/* P50 — median */}
          <ReferenceLine
            x={rankP50}
            stroke="#2563eb"
            strokeWidth={2.5}
            label={{ value: `P50 (${rankP50})`, fill: "#2563eb", fontSize: 11, position: "top" }}
          />
          {/* P90 — worst realistic outcome */}
          <ReferenceLine
            x={rankP90}
            stroke="#dc2626"
            strokeWidth={2}
            strokeDasharray="4 2"
            label={{ value: `P90 (${rankP90})`, fill: "#dc2626", fontSize: 11, position: "top" }}
          />

          <Bar
            dataKey="count"
            fill="#37003c"
            radius={[3, 3, 0, 0]}
            // Single colour, opacity modulated by distance from median
            fillOpacity={0.85}
          />
        </BarChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="mt-2 flex items-center justify-center gap-6 text-xs text-gray-500">
        <span className="flex items-center gap-1">
          <span className="inline-block h-0.5 w-6 border-t-2 border-dashed border-green-600" />
          P10 (best-ish)
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-0.5 w-6 border-t-2 border-blue-600" />
          P50 (median)
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-0.5 w-6 border-t-2 border-dashed border-red-600" />
          P90 (worst-ish)
        </span>
      </div>
    </div>
  );
}
