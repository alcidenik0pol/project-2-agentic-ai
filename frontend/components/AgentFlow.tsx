"use client";

import type { AgentState } from "@/lib/types";

interface AgentFlowProps {
  agents: AgentState[];
}

const AGENT_LABELS: Record<string, string> = {
  orchestrator: "Orchestrator",
  analyst: "Analyst",
  hypothesis: "Hypothesis",
};

export function AgentFlow({ agents }: AgentFlowProps) {
  return (
    <div className="space-y-2">
      <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
        Agent Pipeline
      </div>
      <div className="flex items-center justify-between gap-2">
        {agents.map((agent, i) => (
          <div key={agent.name} className="flex items-center gap-2 flex-1">
            {/* Agent node */}
            <div
              className={`
                relative flex flex-col items-center justify-center
                border-2 px-3 py-2 min-w-[80px] transition-all duration-500
                border-border
                ${agent.status === "running" ? "bg-secondary" : ""}
                ${agent.status === "completed" ? "bg-secondary/50" : ""}
                ${agent.status === "idle" ? "opacity-40" : ""}
              `}
            >
              {/* Active pulse indicator */}
              {agent.status === "running" && (
                <span className="absolute -top-1 -right-1 flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full opacity-75 bg-foreground/50"></span>
                  <span className="relative inline-flex h-2.5 w-2.5 bg-foreground/80"></span>
                </span>
              )}

              {/* Status icon */}
              <span className="text-sm mb-0.5">
                {agent.status === "completed" ? "\u2713" : agent.status === "running" ? "\u25CB" : "\u25CB"}
              </span>

              <span className="text-[10px] font-medium">
                {AGENT_LABELS[agent.name]}
              </span>

              {agent.durationSeconds !== null && (
                <span className="text-[9px] text-muted-foreground mt-0.5">
                  {agent.durationSeconds.toFixed(1)}s
                </span>
              )}
            </div>

            {/* Arrow connector */}
            {i < agents.length - 1 && (
              <div className="flex-shrink-0 text-muted-foreground">
                <svg width="20" height="10" viewBox="0 0 24 12" className="opacity-40">
                  <path d="M0 6h16m0 0l-4-4m4 4l-4 4" stroke="currentColor" strokeWidth="1.5" fill="none" />
                </svg>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
