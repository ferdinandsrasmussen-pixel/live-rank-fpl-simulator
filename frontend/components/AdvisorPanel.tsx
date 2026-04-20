"use client";

import { useState } from "react";
import { Bot, AlertCircle, Users } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SuggestionCard } from "@/components/SuggestionCard";
import { api, type AdvisorResponse, type SimulateResponse } from "@/lib/api";
import { getSessionId } from "@/lib/session";

interface AdvisorPanelProps {
  simulateResult: SimulateResponse | null;
  entryId: number;
  gw: number;
}

export function AdvisorPanel({ simulateResult, entryId, gw }: AdvisorPanelProps) {
  const [budget, setBudget] = useState(0.5);
  const [freeTransfers, setFreeTransfers] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AdvisorResponse | null>(null);

  async function run() {
    if (!simulateResult) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.advisor({
        run_id: simulateResult.run_id,
        budget,
        free_transfers: freeTransfers,
        session_id: getSessionId(),
        entry_id: entryId,
        gw,
      });
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Advisor failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-[#37003c]" />
            AI Transfer Advisor
          </CardTitle>
          <CardDescription>
            Two Cohere LLM calls: Call 1 scores each player&apos;s sell urgency, Call 2 recommends transfers.
            Each recommendation is then re-validated with a fresh Monte Carlo run to show projected rank impact.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!simulateResult ? (
            <div className="flex items-center gap-2 rounded-md bg-amber-50 border border-amber-200 p-4 text-sm text-amber-800">
              <AlertCircle className="h-4 w-4 shrink-0" />
              Run the rank simulation first — the advisor needs those results to validate each transfer.
            </div>
          ) : (
            <>
              <div className="mb-4 grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-xs font-medium text-gray-600">
                    Available budget (£m)
                  </label>
                  <input
                    type="number"
                    value={budget}
                    step={0.1}
                    min={0}
                    max={20}
                    onChange={(e) => setBudget(Number(e.target.value))}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#37003c]"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-gray-600">
                    Free transfers
                  </label>
                  <select
                    value={freeTransfers}
                    onChange={(e) => setFreeTransfers(Number(e.target.value))}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#37003c]"
                  >
                    {[0, 1, 2, 3, 4, 5].map((n) => (
                      <option key={n} value={n}>{n}</option>
                    ))}
                  </select>
                </div>
              </div>

              <Button onClick={run} disabled={loading} className="gap-2">
                <Bot className="h-4 w-4" />
                {loading ? "Running LLM pipeline…" : "Get AI transfer advice"}
              </Button>

              {loading && (
                <p className="mt-2 text-xs text-gray-500">
                  Call 1: squad risk analysis → Call 2: transfer recommendations → Monte Carlo validation per suggestion…
                </p>
              )}
            </>
          )}

          {error && (
            <div className="mt-3 rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-700">
              {error}
            </div>
          )}
        </CardContent>
      </Card>

      {result && (
        <>
          {/* Community RAG signal badge */}
          {result.community_context_used && (
            <div className="flex items-center gap-2 rounded-md bg-blue-50 border border-blue-200 px-4 py-2.5 text-sm text-blue-800">
              <Users className="h-4 w-4 shrink-0" />
              <span>
                <strong>Community-informed</strong> — this advice was shaped by{" "}
                <strong>{result.community_votes_count}</strong> past community vote
                {result.community_votes_count !== 1 ? "s" : ""}. Rejected patterns were injected into the LLM prompt.
              </span>
            </div>
          )}

          {/* Risk analysis table */}
          {result.risk_analysis.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Squad risk analysis</CardTitle>
                <CardDescription>
                  LLM Call 1 scored each starting XI player for sell urgency (1 = keep, 10 = sell immediately).
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-100 text-left text-xs text-gray-500">
                        <th className="pb-2 pr-4">Player</th>
                        <th className="pb-2 pr-4">Pos</th>
                        <th className="pb-2 pr-4 text-center">Urgency</th>
                        <th className="pb-2">Reasoning</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.risk_analysis
                        .sort((a, b) => b.sell_urgency - a.sell_urgency)
                        .map((r) => (
                          <tr key={r.element_id} className="border-b border-gray-50">
                            <td className="py-2 pr-4 font-medium">{r.name}</td>
                            <td className="py-2 pr-4">
                              <Badge variant="secondary" className="text-xs">{r.position}</Badge>
                            </td>
                            <td className="py-2 pr-4 text-center">
                              <span
                                className={`inline-flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold ${
                                  r.sell_urgency >= 7
                                    ? "bg-red-100 text-red-700"
                                    : r.sell_urgency >= 5
                                    ? "bg-amber-100 text-amber-700"
                                    : "bg-green-100 text-green-700"
                                }`}
                              >
                                {r.sell_urgency}
                              </span>
                            </td>
                            <td className="py-2 text-xs text-gray-600">{r.reasoning}</td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Transfer recommendations */}
          {result.recommendations.length > 0 ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-gray-900">Transfer recommendations</h3>
                <p className="text-xs text-gray-500">
                  Current rank P50: <strong>{result.current_rank_p50}</strong>
                </p>
              </div>
              <p className="text-xs text-gray-500">
                Each recommendation is re-run through the full rank simulation — the rank improvement shown is real Monte Carlo output.
                Vote 👍/👎 to help the AI learn what advice actually works.
              </p>
              {result.recommendations.map((rec, i) => (
                <SuggestionCard key={i} rec={rec} isFeatured={rec.rank === 1} />
              ))}
            </div>
          ) : (
            <div className="flex items-center gap-2 rounded-md bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
              <AlertCircle className="h-4 w-4 shrink-0" />
              {result.message ?? "No transfer recommendations generated. Try increasing your budget or running again."}
            </div>
          )}
        </>
      )}
    </div>
  );
}
