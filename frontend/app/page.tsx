"use client";

import { useCallback, useState } from "react";
import { ChatInterface } from "@/components/ChatInterface";
import { ResultsDisplay } from "@/components/ResultsDisplay";
import { useGlobalWebSocket } from "@/hooks/useGlobalWebSocket";
import { useAnalysis } from "@/contexts/AnalysisContext";
import type { AnalysisPhase } from "@/lib/types";

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
  } = useGlobalWebSocket();

  // Combine phases: use the more advanced state
  const phase: AnalysisPhase =
    wsPhase === "running" || analysisPhase === "running" ? "running" :
    wsPhase === "completed" ? "completed" :
    wsPhase === "failed" ? "failed" :
    analysisPhase;

  const error = wsError || analysisError;

  const handleSubmit = useCallback(async (query: string, mode: "test" | "live") => {
    setHasFetched(false);
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
          <div className="flex items-center gap-1 px-4 pt-4 pb-2">
            {agents.map((agent, idx) => {
              const labels = ["Collector (fetch posts)", "Analyst (classify, cluster)", "Hypothesis (generate, save)"];
              const stepNum = idx + 1;
              const isActive = agent.status === "running";
              const isDone = agent.status === "completed";
              return (
                <div key={agent.name} className="flex-1 flex flex-col items-center gap-1">
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
                  <span className={`text-[10px] ${isActive || isDone ? "text-foreground" : "text-muted-foreground"}`}>
                    {labels[idx]}
                  </span>
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

      {/* Error display */}
      {error && (
        <div className="w-full max-w-[700px] mb-4 p-3 bg-secondary border border-border text-foreground text-sm">
          {error}
        </div>
      )}

      {/* Results area - centered, max-width */}
      <div className="w-full max-w-[700px]">
        {(phase === "completed" || hypothesis || reportContent) && (
          <ResultsDisplay
            hypothesis={hypothesis}
            reportContent={reportContent}
          />
        )}
        {phase === "idle" && !hypothesis && !reportContent && (
          <div className="flex items-center justify-center h-[400px] border border-dashed border-border text-muted-foreground">
            <div className="text-center">
              <div className="text-4xl mb-4 opacity-20">
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="mx-auto"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
              </div>
              <p className="text-sm">Enter a topic above to start analyzing Reddit complaints</p>
              <p className="text-xs mt-1 opacity-50">Try &quot;gaming complaints&quot; or &quot;remote work pain points&quot;</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
