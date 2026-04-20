"use client";

import { useState } from "react";
import { RefreshCw, ThumbsUp, ThumbsDown } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type MetaAnalysisData } from "@/lib/api";

interface MetaAnalysisProps {
  initial?: MetaAnalysisData | null;
}

export function MetaAnalysis({ initial }: MetaAnalysisProps) {
  const [data, setData] = useState<MetaAnalysisData | null>(initial ?? null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runAnalysis() {
    setLoading(true);
    setError(null);
    try {
      const result = await api.runMeta();
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to run meta-analysis");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">
            🔁 What the community thinks
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={runAnalysis}
            disabled={loading}
            className="gap-1.5"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            {loading ? "Analysing..." : "Refresh analysis"}
          </Button>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          The AI reads all community votes and identifies patterns — what advice people liked, what they rejected.
          {data?.gameweek_range && (
            <span className="ml-1 text-gray-400">({data.gameweek_range})</span>
          )}
        </p>
      </CardHeader>

      <CardContent>
        {error && (
          <div className="rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-700 mb-4">
            {error}
          </div>
        )}

        {!data?.summary && !loading && (
          <div className="rounded-md bg-gray-50 p-4 text-sm text-gray-500 text-center">
            No community analysis yet. Cast some votes on suggestions, then click{" "}
            <strong>Refresh analysis</strong>.
          </div>
        )}

        {data?.summary && (
          <div className="space-y-4">
            <p className="text-sm text-gray-700 leading-relaxed">{data.summary}</p>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {data.liked_patterns && data.liked_patterns.length > 0 && (
                <div className="rounded-lg bg-green-50 border border-green-200 p-3">
                  <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-green-800">
                    <ThumbsUp className="h-3.5 w-3.5" />
                    Community liked
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {data.liked_patterns.map((p, i) => (
                      <Badge key={i} variant="success" className="text-xs">
                        {p}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {data.rejected_patterns && data.rejected_patterns.length > 0 && (
                <div className="rounded-lg bg-red-50 border border-red-200 p-3">
                  <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-red-800">
                    <ThumbsDown className="h-3.5 w-3.5" />
                    Community rejected
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {data.rejected_patterns.map((p, i) => (
                      <Badge key={i} variant="destructive" className="text-xs">
                        {p}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {data.created_at && (
              <p className="text-right text-xs text-gray-400">
                Last updated: {new Date(data.created_at).toLocaleString()}
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
