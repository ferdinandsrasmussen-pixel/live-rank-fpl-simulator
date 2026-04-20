"use client";

import { useState } from "react";
import { ThumbsUp, ThumbsDown, ArrowRight, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type Recommendation } from "@/lib/api";
import { getSessionId } from "@/lib/session";

const confidenceConfig = {
  High: { variant: "success" as const, label: "High confidence" },
  Medium: { variant: "warning" as const, label: "Medium confidence" },
  Low: { variant: "destructive" as const, label: "Low confidence" },
};

interface SuggestionCardProps {
  rec: Recommendation;
  isFeatured?: boolean;
}

export function SuggestionCard({ rec, isFeatured = false }: SuggestionCardProps) {
  const [thumbsUp, setThumbsUp] = useState(rec.thumbs_up);
  const [thumbsDown, setThumbsDown] = useState(rec.thumbs_down);
  const [userVote, setUserVote] = useState<number | null | undefined>(rec.user_vote);
  const [voting, setVoting] = useState(false);

  const rankDelta = rec.rank_improvement;
  const conf = confidenceConfig[rec.confidence] ?? confidenceConfig.Medium;

  async function vote(value: 1 | -1) {
    if (!rec.suggestion_id || voting) return;
    setVoting(true);
    try {
      const result = await api.castVote(rec.suggestion_id, getSessionId(), value);
      setThumbsUp(result.thumbs_up);
      setThumbsDown(result.thumbs_down);
      setUserVote(value);
    } catch {
      // fail silently — vote not critical
    } finally {
      setVoting(false);
    }
  }

  return (
    <Card className={isFeatured ? "border-[#37003c] border-2" : ""}>
      <CardContent className="pt-5">
        {/* Header row */}
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <span className="flex items-center gap-2 text-sm font-semibold text-gray-900">
            <span>{rec.player_out}</span>
            <ArrowRight className="h-4 w-4 text-gray-400" />
            <span className="text-[#37003c]">{rec.player_in}</span>
          </span>
          <Badge variant={conf.variant}>{conf.label}</Badge>
          {rec.cost_hit > 0 && (
            <Badge variant="destructive">-{rec.cost_hit * 4} pts hit</Badge>
          )}
          <Badge variant="secondary">{rec.position}</Badge>
        </div>

        {/* Rank impact metrics */}
        {rec.projected_rank_p50 !== undefined && (
          <div className="mb-3 flex flex-wrap gap-4 rounded-lg bg-gray-50 px-4 py-3">
            <div className="text-center">
              <p className="text-xs text-gray-500">Projected rank (P50)</p>
              <p className="text-lg font-bold text-gray-900">{rec.projected_rank_p50}</p>
            </div>
            <div className="text-center">
              <p className="text-xs text-gray-500">Range (P10–P90)</p>
              <p className="text-sm font-semibold text-gray-700">
                {rec.projected_rank_p10} – {rec.projected_rank_p90}
              </p>
            </div>
            {rankDelta !== undefined && (
              <div className="flex items-center gap-1 text-sm font-semibold">
                {rankDelta > 0 ? (
                  <>
                    <TrendingUp className="h-4 w-4 text-green-600" />
                    <span className="text-green-700">+{rankDelta} rank places</span>
                  </>
                ) : rankDelta < 0 ? (
                  <>
                    <TrendingDown className="h-4 w-4 text-red-600" />
                    <span className="text-red-700">{rankDelta} rank places</span>
                  </>
                ) : (
                  <>
                    <Minus className="h-4 w-4 text-gray-400" />
                    <span className="text-gray-500">Rank unchanged</span>
                  </>
                )}
              </div>
            )}
          </div>
        )}

        {/* Reasoning */}
        <p className="mb-4 text-sm text-gray-600 leading-relaxed">{rec.reasoning}</p>

        {/* Vote bar */}
        <div className="flex items-center justify-between border-t border-gray-100 pt-3">
          <span className="text-xs text-gray-400">Was this suggestion useful?</span>
          <div className="flex items-center gap-2">
            <Button
              variant={userVote === 1 ? "success" : "ghost"}
              size="sm"
              onClick={() => vote(1)}
              disabled={voting}
              className="gap-1"
            >
              <ThumbsUp className="h-3.5 w-3.5" />
              <span>{thumbsUp}</span>
            </Button>
            <Button
              variant={userVote === -1 ? "destructive" : "ghost"}
              size="sm"
              onClick={() => vote(-1)}
              disabled={voting}
              className="gap-1"
            >
              <ThumbsDown className="h-3.5 w-3.5" />
              <span>{thumbsDown}</span>
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
