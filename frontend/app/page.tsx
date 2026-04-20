"use client";

import { useEffect, useRef, useState } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { DemoBanner } from "@/components/DemoBanner";
import { SimulatorPanel } from "@/components/SimulatorPanel";
import { AdvisorPanel } from "@/components/AdvisorPanel";
import { MetaAnalysis } from "@/components/MetaAnalysis";
import { StatsBar } from "@/components/StatsBar";
import { api, type SimulateResponse, type MetaAnalysisData } from "@/lib/api";

const DEMO_ENTRY_ID = 860655;
const DEMO_LEAGUE_ID = 130708;

export default function Home() {
  const [isDemoMode, setIsDemoMode] = useState(true);
  const [entryId, setEntryId] = useState(DEMO_ENTRY_ID);
  const [gw, setGw] = useState(33); // overridden on mount by /api/current-gw
  const [simulateResult, setSimulateResult] = useState<SimulateResponse | null>(null);
  const [metaData, setMetaData] = useState<MetaAnalysisData | null>(null);
  const [activeTab, setActiveTab] = useState("simulator");
  const [demoError, setDemoError] = useState<string | null>(null);
  const hasAutoRun = useRef(false);

  // Fetch current GW and meta on mount
  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    fetch(`${base}/api/current-gw`)
      .then((r) => r.json())
      .then((d) => { if (d.gw) setGw(d.gw); })
      .catch(() => null);

    api.getMeta().then(setMetaData).catch(() => null);
  }, []);

  // Demo auto-run: immediately kick off the simulation so the professor
  // lands on real results without any interaction
  useEffect(() => {
    if (!isDemoMode || hasAutoRun.current) return;
    hasAutoRun.current = true;

    // Fetch current GW from FPL bootstrap via backend
    fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/health`)
      .then(() =>
        api.simulate({
          entry_id: DEMO_ENTRY_ID,
          gw: gw || 1,
          league_id: DEMO_LEAGUE_ID,
          mode: "Pre-GW",
          n_sims: 2000,
          rivals_to_sim: 8,
        })
      )
      .then((res) => {
        setSimulateResult(res);
      })
      .catch((e) => {
        setDemoError(e instanceof Error ? e.message : "Demo simulation failed");
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isDemoMode]);

  function dismissDemo() {
    setIsDemoMode(false);
    setSimulateResult(null);
    setEntryId(0);
  }

  return (
    <div className="flex min-h-screen flex-col">
      {/* FPL-purple header */}
      <header className="bg-[#37003c] text-white">
        {isDemoMode && <DemoBanner onDismiss={dismissDemo} />}
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight">
              FPL Mini-League Rank Simulator
              <span className="ml-2 rounded bg-[#00ff87] px-1.5 py-0.5 text-xs font-bold text-[#37003c]">
                v2
              </span>
            </h1>
            <p className="mt-0.5 text-xs text-purple-200">
              Monte Carlo simulation · Cohere LLM advisor · Community feedback loop
            </p>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-6">
        {demoError && (
          <div className="mb-4 rounded-md bg-amber-50 border border-amber-200 p-3 text-sm text-amber-800">
            Demo auto-run: {demoError}. Use the Simulator tab to run manually.
          </div>
        )}

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-6">
            <TabsTrigger value="simulator">Rank Simulator</TabsTrigger>
            <TabsTrigger value="advisor">AI Transfer Advisor</TabsTrigger>
            <TabsTrigger value="community">Community</TabsTrigger>
          </TabsList>

          <TabsContent value="simulator">
            <SimulatorPanel
              defaultEntryId={isDemoMode ? DEMO_ENTRY_ID : 0}
              defaultLeagueId={isDemoMode ? DEMO_LEAGUE_ID : 0}
              defaultGw={gw}
              onSimulated={(res) => setSimulateResult(res)}
              externalResult={simulateResult}
              isDemo={isDemoMode}
            />
          </TabsContent>

          <TabsContent value="advisor">
            <AdvisorPanel
              simulateResult={simulateResult}
              entryId={isDemoMode ? DEMO_ENTRY_ID : entryId}
              gw={gw || 1}
            />
          </TabsContent>

          <TabsContent value="community">
            <div className="space-y-6">
              <MetaAnalysis initial={metaData} />

              <div className="rounded-xl border border-gray-200 bg-white p-5 text-sm text-gray-600 shadow-sm">
                <h3 className="mb-2 font-semibold text-gray-900">How the feedback loop works</h3>
                <ol className="list-decimal pl-5 space-y-1.5">
                  <li>
                    <strong>Layer 1 — Collection</strong>: Every transfer suggestion has 👍/👎 vote buttons.
                    Votes are stored per-suggestion (keyed on gameweek + players), so they aggregate
                    across all users who received the same recommendation.
                  </li>
                  <li>
                    <strong>Layer 2 — RAG injection</strong>: The next time any user runs the AI advisor,
                    suggestions with ≤ −2 net votes are injected into the LLM prompt as context:{" "}
                    <em>&quot;The community rejected these transfers — factor this into your confidence.&quot;</em>
                  </li>
                  <li>
                    <strong>Layer 3 — Meta-analysis</strong>: Click{" "}
                    <strong>Refresh analysis</strong> above to run a Cohere call that reads all vote patterns
                    and surfaces what the community consistently liked or rejected.
                  </li>
                </ol>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </main>

      <footer className="mt-auto">
        <StatsBar />
        <div className="border-t border-gray-100 py-3 text-center text-xs text-gray-400">
          ESADE PDAI 2025-26 · Assignment 3 · Built with FastAPI + Next.js 14 + Cohere
        </div>
      </footer>
    </div>
  );
}
