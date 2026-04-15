"use client";

import { LogViewer } from "@/components/LogViewer";
import { useGlobalWebSocket } from "@/hooks/useGlobalWebSocket";
import Link from "next/link";

export default function DebugPage() {
  const { logs, phase, currentActivity, agents } = useGlobalWebSocket();

  return (
    <div className="flex flex-col items-center px-4 py-8">
      <div className="w-full max-w-4xl">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-lg font-bold mb-1">Debug Logs</h1>
            <p className="text-xs text-muted-foreground">
              Real-time log stream from the multi-agent pipeline. Logs are streamed via WebSocket
              and persist across page navigation.
            </p>
          </div>
          <div className="flex items-center gap-3">
            {phase === "running" && (
              <div className="flex items-center gap-2">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                </span>
                <span className="text-xs text-muted-foreground">
                  {currentActivity || "Running..."}
                </span>
              </div>
            )}
            {phase === "idle" && (
              <span className="text-xs text-muted-foreground">No active analysis</span>
            )}
          </div>
        </div>

        <div className="border border-border bg-card p-4">
          {logs.length === 0 ? (
            <div className="text-center py-16 text-muted-foreground">
              <p className="text-sm mb-2">No logs yet</p>
              <p className="text-xs">
                {phase === "idle"
                  ? "Start an analysis on the home page to see logs here."
                  : "Waiting for log entries..."}
              </p>
            </div>
          ) : (
            <LogViewer logs={logs} />
          )}
        </div>

        {/* Agent status summary */}
        {phase !== "idle" && (
          <div className="mt-4 border border-border bg-card p-4">
            <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">
              Agent Status
            </h2>
            <div className="flex gap-4">
              {agents.map((agent) => {
                const labels: Record<string, string> = {
                  orchestrator: "Collector",
                  analyst: "Analyst",
                  hypothesis: "Hypothesis",
                  subreddit_selector: "Subreddit Selector",
                };
                return (
                  <div key={agent.name} className="flex items-center gap-2">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        agent.status === "running"
                          ? "bg-blue-400 animate-pulse"
                          : agent.status === "completed"
                          ? "bg-green-400"
                          : "bg-muted-foreground/30"
                      }`}
                    />
                    <span className="text-xs">{labels[agent.name]}</span>
                    {agent.durationSeconds !== null && (
                      <span className="text-[10px] text-muted-foreground">
                        ({agent.durationSeconds.toFixed(1)}s)
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <div className="mt-4">
          <Link
            href="/"
            className="text-xs text-muted-foreground hover:text-foreground transition-colors underline"
          >
            Back to Home
          </Link>
        </div>
      </div>
    </div>
  );
}
