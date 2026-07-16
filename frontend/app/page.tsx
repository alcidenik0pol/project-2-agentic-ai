"use client";

import { useCallback, useEffect, useRef, useState, useMemo } from "react";
import { ChatInterface } from "@/components/ChatInterface";
import { TabbedResultsDisplay } from "@/components/TabbedResultsDisplay";
import { CollectorPacingInfo } from "@/components/CollectorPacingInfo";
import { LogViewer } from "@/components/LogViewer";
import { useGlobalWebSocket } from "@/hooks/useGlobalWebSocket";
import { useAnalysis } from "@/contexts/AnalysisContext";
import { getZipUrl } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Download, CheckCircle2, ChevronDown, ChevronUp } from "lucide-react";
import type { AnalysisPhase, DataSource } from "@/lib/types";
import confetti from "canvas-confetti";

export default function Home() {
  const {
    phase: analysisPhase,
    reportContent,
    error: analysisError,
    submit,
    fetchResults,
    reset: resetAnalysis,
    dataSource,
  } = useAnalysis();

  const [lastQuery, setLastQuery] = useState<string>("");
  const [hasFlashed, setHasFlashed] = useState<Record<string, boolean>>({});
  const [logExpanded, setLogExpanded] = useState(true);

  const {
    runId,
    phase: wsPhase,
    agents,
    logs,
    error: wsError,
    connect,
    cancelAnalysis,
    reset: resetWs,
    prepareNewRun,
    currentActivity,
    progressPercent,
    classificationEDA,
    clusteringEDA,
    hypothesis,
    rateLimit,
    agentProgress,
    elapsed,
    connectionStatus,
  } = useGlobalWebSocket();

  // Combined phase: error states take highest priority so failures are never
  // hidden by a stale idle/submitting state.  Then running > submitting > completed.
  const phase: AnalysisPhase =
    wsPhase === "failed" ? "failed" :
    analysisPhase === "failed" ? "failed" :
    wsPhase === "running" ? "running" :
    analysisPhase === "submitting" ? "submitting" :
    wsPhase === "completed" ? "completed" :
    analysisPhase;

  const error = wsError || analysisError;

  // Debug: log phase resolution every render
  useEffect(() => {
    console.log("[Page] Phase resolution:", {
      wsPhase,
      analysisPhase,
      resolved: phase,
      wsError,
      analysisError,
      resolvedError: error,
      runId,
      connectionStatus,
    });
  });

  const elapsedStr = useMemo(() => {
    const m = Math.floor(elapsed / 60);
    const s = elapsed % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  }, [elapsed]);

  // Fire confetti once when analysis completes successfully
  const confettiFired = useRef(false);
  useEffect(() => {
    if (phase === "completed" && hypothesis && !confettiFired.current) {
      confettiFired.current = true;
      // Left burst
      confetti({ particleCount: 60, spread: 55, origin: { x: 0.15, y: 0.65 }, colors: ["#22c55e", "#4ade80", "#86efac", "#fbbf24", "#f59e0b"] });
      // Right burst
      confetti({ particleCount: 60, spread: 55, origin: { x: 0.85, y: 0.65 }, colors: ["#22c55e", "#4ade80", "#86efac", "#fbbf24", "#f59e0b"] });
      // Center shower
      setTimeout(() => {
        confetti({ particleCount: 40, spread: 70, origin: { y: 0.6 }, colors: ["#22c55e", "#4ade80", "#86efac", "#fbbf24", "#f59e0b"] });
      }, 250);
    }
  }, [phase, hypothesis]);

  // Track which agents have already flashed on completion
  useEffect(() => {
    agents.forEach(agent => {
      if (agent.status === "completed" && !hasFlashed[agent.name]) {
        setHasFlashed(prev => ({ ...prev, [agent.name]: true }));
      }
    });
  }, [agents, hasFlashed]);

  const handleSubmit = useCallback(async (query: string, dataSource: DataSource) => {
    console.log("[Page] handleSubmit called", { query, dataSource });
    setHasFetched(false);
    setLastQuery(query);
    setHasFlashed({});
    confettiFired.current = false;

    console.log("[Page] handleSubmit: calling prepareNewRun()");
    // Reset UI state for a new run without closing the WS.
    // connect() will atomically close old WS and create new one.
    prepareNewRun();

    console.log("[Page] handleSubmit: calling resetAnalysis()");
    resetAnalysis();

    console.log("[Page] handleSubmit: calling submit()");
    const id = await submit(query, dataSource);
    if (!id) {
      console.error("[Page] handleSubmit: submit() returned null — API call failed", {
        query,
        dataSource,
        analysisPhase,
        wsPhase,
      });
      return;
    }
    console.log(`[Page] handleSubmit: submit() returned run_id=${id}, calling connect()`);
    connect(id);
  }, [submit, connect, prepareNewRun, resetAnalysis, analysisPhase, wsPhase]);

  const handleCancel = useCallback(() => {
    console.log("[Page] handleCancel called", { runId, wsPhase, analysisPhase });
    cancelAnalysis();
    resetAnalysis();
    // Don't reset WS here - let it stay alive to receive the cancellation
    // confirmation from backend. The analysis_cancelled handler in
    // WebSocketContext will transition phase to "idle" cleanly.
  }, [cancelAnalysis, resetAnalysis, runId, wsPhase, analysisPhase]);

  const handleReset = useCallback(() => {
    console.log("[Page] handleReset called", { runId, wsPhase, analysisPhase });
    resetWs();
    resetAnalysis();
    setLastQuery("");
    setHasFetched(false);
    setHasFlashed({});
    confettiFired.current = false;
    console.log("[Page] handleReset complete — all state reset to idle");
  }, [resetWs, resetAnalysis, runId, wsPhase, analysisPhase]);

  // Auto-fetch results when WebSocket reports completion
  const [hasFetched, setHasFetched] = useState(false);

  useEffect(() => {
    if (wsPhase === "completed" && !hasFetched && runId) {
      console.log("[Page] Auto-fetching results", { runId, wsPhase, hasFetched });
      setHasFetched(true);
      fetchResults();
    }
    // Reset hasFetched when starting a new run
    if (wsPhase === "running" && hasFetched) {
      console.log("[Page] Resetting hasFetched (new run started)");
      setHasFetched(false);
    }
    // Also reset when wsPhase becomes "idle" (cancelled)
    if (wsPhase === "idle" && hasFetched) {
      console.log("[Page] Resetting hasFetched (wsPhase=idle)");
      setHasFetched(false);
    }
  }, [wsPhase, hasFetched, runId, fetchResults]);

  return (
    <div className="flex-1 flex flex-col items-center px-4 py-8">
      {/* Chat input */}
      <div className="w-full max-w-[700px] mb-6">
        <ChatInterface
          onSubmit={handleSubmit}
          phase={phase}
          onCancel={handleCancel}
          onReset={handleReset}
        />
      </div>

      {/* Progress panel - visible during analysis */}
      {phase === "running" && (
        <div className="w-full max-w-[700px] mb-4 border border-border bg-card">
          {/* Step indicators */}
          <div className="flex items-center gap-1 px-4 pt-4 pb-2 relative">
            <span className="absolute right-4 top-4 text-[10px] font-mono text-muted-foreground tabular-nums">
              {elapsedStr}
            </span>
            {agents.map((agent, idx) => {
              const labels = ["Collector", "Analyst", "Hypothesis"];
              const sublabels = ["fetch posts", "classify, cluster", "generate, save"];
              const timeEstimates = ["~4m", "~3m", "~1.5m"];
              const stepNum = idx + 1;
              const isActive = agent.status === "running";
              const isDone = agent.status === "completed";
              return (
                <div key={agent.name} className="flex-1 flex flex-col items-center gap-0.5">
                  <div
                    className={`w-7 h-7 flex items-center justify-center text-xs font-medium border ${
                      isDone
                        ? "bg-green-600 dark:bg-green-500 text-white border-green-600 dark:border-green-500"
                        : isActive
                        ? "agent-step-active"
                        : "bg-card text-muted-foreground border-border"
                    } ${isDone && !hasFlashed[agent.name] ? "animate-step-complete-flash" : ""}`}
                  >
                    {isDone ? "\u2713" : stepNum}
                  </div>
                  <span className={`text-[10px] ${isActive || isDone ? "text-foreground font-medium" : "text-muted-foreground"}`}>
                    {labels[idx]}
                  </span>
                  {!isDone && (
                    <span className="text-[9px] text-muted-foreground/70 truncate max-w-full px-1">
                      {sublabels[idx]}
                    </span>
                  )}
                  {!isDone && (
                    <span className="text-[9px] text-muted-foreground/60 font-mono">
                      {timeEstimates[idx]}
                    </span>
                  )}
                  {isDone && (
                    <span className="text-[9px] text-green-600 dark:text-green-400">
                      Completed
                    </span>
                  )}
                </div>
              );
            })}
          </div>

          {/* Progress bar */}
          <div className="px-4 pb-2">
            <div className="w-full h-1.5 bg-secondary">
              <div
                className="h-full bg-primary transition-all duration-500 ease-out"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>

          {/* Current activity */}
          {currentActivity && (
            <div className="px-4 pb-2">
              <p className="text-xs text-muted-foreground truncate">{currentActivity}</p>
            </div>
          )}
        </div>
      )}

      {/* Collapsible Activity Log - persists across running/completed/failed */}
      {logs.length > 0 && (
        <div className="w-full max-w-[700px] mb-4 border border-border bg-card">
          <button
            onClick={() => setLogExpanded((v) => !v)}
            className="w-full flex items-center justify-between px-4 py-2 text-left"
          >
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Activity Log ({logs.length})
            </span>
            {logExpanded ? (
              <ChevronUp className="w-4 h-4 text-muted-foreground" />
            ) : (
              <ChevronDown className="w-4 h-4 text-muted-foreground" />
            )}
          </button>
          {logExpanded && (
            <div className="border-t border-border px-4 py-2">
              <LogViewer logs={logs} />
            </div>
          )}
        </div>
      )}

      {/* Collector pacing info - only during collector phase, for live Reddit sources */}
      {phase === "running" && agents[0]?.status === "running" && (dataSource === "reddit_live" || dataSource === "reddit_v2") && (
        <div className="w-full max-w-[700px] mb-4 border border-border bg-card p-4">
          <CollectorPacingInfo
            rateLimit={rateLimit}
            agentProgress={agentProgress}
          />
        </div>
      )}

      {/* Error display */}
      {error && (
        <div className="w-full max-w-[700px] mb-4 p-3 bg-secondary border border-border text-foreground text-sm">
          {error}
        </div>
      )}

      {/* Results area - centered, max-width */}
      <div className="w-full max-w-[700px]">
        {phase === "completed" && hypothesis && (
          <div className="mb-4 px-3 py-2 bg-green-500/10 border border-green-500/30 rounded-md flex flex-col sm:flex-row items-center gap-2">
            <span className="text-green-500 text-sm font-medium flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4" />
              Analysis complete
            </span>
            <span className="text-xs text-muted-foreground">Your report is ready below.</span>
            <div className="sm:ml-auto">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  if (!runId) return;
                  window.open(getZipUrl(runId), "_blank");
                }}
                disabled={!runId}
              >
                <Download className="w-4 h-4 mr-2" />
                Download ZIP
              </Button>
            </div>
          </div>
        )}
        {(phase === "completed" || hypothesis || classificationEDA || clusteringEDA) && (
          <TabbedResultsDisplay
            hypothesis={hypothesis}
            classificationEDA={classificationEDA}
            clusteringEDA={clusteringEDA}
            query={lastQuery}
            generationComplete={wsPhase === "completed" && hasFetched}
          />
        )}
      </div>
    </div>
  );
}
