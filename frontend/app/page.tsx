"use client";

import { useCallback, useEffect, useRef, useState, useMemo } from "react";
import { ChatInterface } from "@/components/ChatInterface";
import { TabbedResultsDisplay } from "@/components/TabbedResultsDisplay";
import { CollectorPacingInfo } from "@/components/CollectorPacingInfo";
import { useGlobalWebSocket } from "@/hooks/useGlobalWebSocket";
import { useAnalysis } from "@/contexts/AnalysisContext";
import type { AnalysisPhase } from "@/lib/types";
import confetti from "canvas-confetti";

export default function Home() {
  const {
    phase: analysisPhase,
    hypothesis,
    reportContent,
    error: analysisError,
    submit,
    fetchResults,
    reset: resetAnalysis,
  } = useAnalysis();

  const [lastQuery, setLastQuery] = useState<string>("");

  const {
    runId,
    phase: wsPhase,
    agents,
    logs,
    error: wsError,
    connect,
    cancelAnalysis,
    reset: resetWs,
    currentActivity,
    progressPercent,
    classificationEDA,
    clusteringEDA,
    rateLimit,
    agentProgress,
  } = useGlobalWebSocket();

  // Combine phases: wsPhase completion takes priority over analysisPhase running
  // This prevents the input from being disabled during fetchResults() after ws completes
  const phase: AnalysisPhase =
    wsPhase === "completed" ? "completed" :
    wsPhase === "failed" ? "failed" :
    wsPhase === "running" || analysisPhase === "running" ? "running" :
    analysisPhase;

  const error = wsError || analysisError;

  // Elapsed timer: counts seconds while phase === "running"
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    if (phase !== "running") {
      setElapsed(0);
      return;
    }
    const interval = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(interval);
  }, [phase]);

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
    if (phase !== "completed") {
      confettiFired.current = false;
    }
  }, [phase, hypothesis]);

  const handleSubmit = useCallback(async (query: string, mode: "test" | "live") => {
    setHasFetched(false);
    setLastQuery(query);
    resetWs();
    const id = await submit(query, mode);
    if (!id) return;
    connect(id);
  }, [submit, connect, resetWs]);

  const handleCancel = useCallback(() => {
    cancelAnalysis();
    resetAnalysis();
    resetWs();
  }, [cancelAnalysis, resetAnalysis, resetWs]);

  // Auto-fetch results when WebSocket reports completion
  const [hasFetched, setHasFetched] = useState(false);
  if (wsPhase === "completed" && !hasFetched && runId) {
    setHasFetched(true);
    fetchResults();
  }

  if (wsPhase === "idle" && hasFetched) {
    setHasFetched(false);
  }

  return (
    <div className="flex-1 flex flex-col items-center px-4 py-6">
      {/* Chat input */}
      <div className="w-full max-w-[700px] mb-6">
        <ChatInterface
          onSubmit={handleSubmit}
          phase={phase}
          onCancel={handleCancel}
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
                        ? "bg-primary text-primary-foreground border-primary"
                        : isActive
                        ? "bg-secondary text-foreground border-foreground animate-pulse"
                        : "bg-card text-muted-foreground border-border"
                    }`}
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

          {/* Recent log lines preview */}
          {logs.length > 0 && (
            <div className="border-t border-border px-4 py-2 max-h-[120px] overflow-y-auto">
              {logs.slice(-5).map((log) => (
                <div key={log.id} className="flex gap-2 text-[10px] font-mono leading-relaxed">
                  <span className={
                    log.level === "ERROR" ? "text-red-400" :
                    log.level === "WARNING" ? "text-yellow-400" :
                    "text-muted-foreground"
                  }>
                    {log.level}
                  </span>
                  <span className="text-foreground truncate">{log.message}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Collector pacing info - only during orchestrator/collector phase */}
      {phase === "running" && agents[0]?.status === "running" && (
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
          <div className="mb-4 px-3 py-2 bg-primary/10 border border-primary/20 rounded-md flex items-center gap-2">
            <span className="text-primary text-sm font-medium">&#10003; Analysis complete</span>
            <span className="text-xs text-muted-foreground">Your report is ready below.</span>
          </div>
        )}
        {(phase === "completed" || hypothesis || classificationEDA || clusteringEDA) && (
          <TabbedResultsDisplay
            hypothesis={hypothesis}
            classificationEDA={classificationEDA}
            clusteringEDA={clusteringEDA}
            query={lastQuery}
            generationComplete={wsPhase === "completed" && hasFetched}
            runId={runId ?? undefined}
          />
        )}
      </div>
    </div>
  );
}
