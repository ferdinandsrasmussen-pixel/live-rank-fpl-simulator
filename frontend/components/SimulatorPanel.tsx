"use client";

import { useState } from "react";
import { Play, Trophy, Target, Users, BarChart2 } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { RankChart } from "@/components/RankChart";
import { api, type SimulateResponse } from "@/lib/api";

interface SimulatorPanelProps {
  defaultEntryId?: number;
  defaultLeagueId?: number;
  defaultGw?: number;
  onSimulated?: (result: SimulateResponse) => void;
  externalResult?: SimulateResponse | null; // pre-populated by demo auto-run
  isDemo?: boolean;
}

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white px-5 py-4 text-center shadow-sm">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-2xl font-bold text-[#37003c]">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

export function SimulatorPanel({
  defaultEntryId = 860655,
  defaultLeagueId = 130708,
  defaultGw = 33,
  onSimulated,
  externalResult,
  isDemo = false,
}: SimulatorPanelProps) {
  const [entryId, setEntryId] = useState(defaultEntryId);
  const [leagueId, setLeagueId] = useState(defaultLeagueId);
  const [gw, setGw] = useState(defaultGw);
  const [mode, setMode] = useState<"Live" | "Pre-GW">("Live");
  const [nSims, setNSims] = useState(2000);
  const [rivalsToSim, setRivalsToSim] = useState(8);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [localResult, setLocalResult] = useState<SimulateResponse | null>(null);

  // Show external (demo auto-run) result if no local run yet
  const result = localResult ?? externalResult ?? null;

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const res = await api.simulate({ entry_id: entryId, gw, league_id: leagueId, mode, n_sims: nSims, rivals_to_sim: rivalsToSim });
      setLocalResult(res);
      onSimulated?.(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Simulation failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Config card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart2 className="h-5 w-5 text-[#37003c]" />
            Mini-league rank simulator
          </CardTitle>
          <CardDescription>
            Runs {nSims.toLocaleString()} Poisson + Bernoulli Monte Carlo simulations to estimate your rank distribution.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Team ID</label>
              <input
                type="number"
                value={entryId}
                onChange={(e) => setEntryId(Number(e.target.value))}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#37003c]"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">League ID</label>
              <input
                type="number"
                value={leagueId}
                onChange={(e) => setLeagueId(Number(e.target.value))}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#37003c]"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Gameweek</label>
              <input
                type="number"
                value={gw}
                min={1}
                max={38}
                onChange={(e) => setGw(Number(e.target.value))}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#37003c]"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Mode</label>
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value as "Live" | "Pre-GW")}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#37003c]"
              >
                <option value="Live">Live (mid-GW)</option>
                <option value="Pre-GW">Pre-GW (forecast)</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Simulations</label>
              <select
                value={nSims}
                onChange={(e) => setNSims(Number(e.target.value))}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#37003c]"
              >
                {[1000, 2000, 5000, 10000].map((n) => (
                  <option key={n} value={n}>{n.toLocaleString()}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Rivals to simulate</label>
              <input
                type="number"
                value={rivalsToSim}
                min={0}
                max={50}
                onChange={(e) => setRivalsToSim(Number(e.target.value))}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#37003c]"
              />
            </div>
          </div>

          <div className="mt-4">
            <Button onClick={run} disabled={loading} className="gap-2">
              <Play className="h-4 w-4" />
              {loading ? "Simulating…" : "Run simulation"}
            </Button>
          </div>

          {error && (
            <div className="mt-3 rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-700">
              {error}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Results */}
      {result && (
        <>
          {/* Summary metrics */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatCard label="Rank P50 (most likely)" value={result.rank_p50} />
            <StatCard
              label="Win probability"
              value={`${(result.p_win * 100).toFixed(0)}%`}
              sub={`Top-3: ${(result.p_top3 * 100).toFixed(0)}%`}
            />
            <StatCard label="Rank P10 (best-ish)" value={result.rank_p10} />
            <StatCard label="Rank P90 (worst-ish)" value={result.rank_p90} />
          </div>

          {/* Points outlook */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <Target className="h-4 w-4" /> Your points outlook
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-6">
                <div>
                  <p className="text-xs text-gray-500">P10 (low-ish)</p>
                  <p className="text-xl font-bold text-gray-900">{result.my_p10}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">P50 (typical)</p>
                  <p className="text-xl font-bold text-[#37003c]">{result.my_p50}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">P90 (high-ish)</p>
                  <p className="text-xl font-bold text-gray-900">{result.my_p90}</p>
                </div>
              </div>
              <p className="mt-2 text-xs text-gray-400">
                In ~80% of simulations you score between <strong>{result.my_p10}</strong> and{" "}
                <strong>{result.my_p90}</strong> points.
              </p>
            </CardContent>
          </Card>

          {/* Rank distribution chart */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Rank distribution</CardTitle>
              <CardDescription>
                Each bar = number of simulations where you finished at that rank.
                P10/P50/P90 reference lines show the probability spread — this is a distribution, not a point estimate.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <RankChart
                data={result.rank_histogram}
                rankP10={result.rank_p10}
                rankP50={result.rank_p50}
                rankP90={result.rank_p90}
              />
            </CardContent>
          </Card>

          {/* Rivals table */}
          {result.rivals_summary.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Users className="h-4 w-4" /> Rivals projected points (P10 / P50 / P90)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-100 text-left text-xs text-gray-500">
                        <th className="pb-2 pr-4">Rank</th>
                        <th className="pb-2 pr-4">Team</th>
                        <th className="pb-2 pr-4 text-right">P10</th>
                        <th className="pb-2 pr-4 text-right">P50</th>
                        <th className="pb-2 text-right">P90</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.rivals_summary
                        .sort((a, b) => a.league_rank - b.league_rank)
                        .map((r) => (
                          <tr key={r.entry} className="border-b border-gray-50">
                            <td className="py-1.5 pr-4 text-gray-500">{r.league_rank}</td>
                            <td className="py-1.5 pr-4 font-medium">{r.name}</td>
                            <td className="py-1.5 pr-4 text-right text-gray-600">{r.p10}</td>
                            <td className="py-1.5 pr-4 text-right font-semibold text-[#37003c]">{r.p50}</td>
                            <td className="py-1.5 text-right text-gray-600">{r.p90}</td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Player projections */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Your players — projected points</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100 text-left text-xs text-gray-500">
                      <th className="pb-2 pr-4">Player</th>
                      <th className="pb-2 pr-4">Pos</th>
                      <th className="pb-2 pr-4 text-right">P10</th>
                      <th className="pb-2 pr-4 text-right">P50</th>
                      <th className="pb-2 text-right">P90</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.player_projections.map((p, i) => (
                      <tr key={i} className="border-b border-gray-50">
                        <td className="py-1.5 pr-4 font-medium">{p.player}</td>
                        <td className="py-1.5 pr-4">
                          <Badge variant="secondary" className="text-xs">{p.pos}</Badge>
                        </td>
                        <td className="py-1.5 pr-4 text-right text-gray-600">{p.p10.toFixed(1)}</td>
                        <td className="py-1.5 pr-4 text-right font-semibold">{p.p50.toFixed(1)}</td>
                        <td className="py-1.5 text-right text-gray-600">{p.p90.toFixed(1)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
