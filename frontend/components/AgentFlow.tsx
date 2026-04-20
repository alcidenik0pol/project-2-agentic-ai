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
      <div className="flex flex-col sm:flex-row items-stretch justify-center gap-2 sm:gap-2">
        {agents.map((agent, i) => (
          <div key={agent.name} className="flex flex-col sm:flex-row items-center gap-2 sm:gap-2 sm:flex-1">
            {/* Agent node */}
            <div
              className={`
                relative flex flex-col items-center justify-start sm:flex-1
                border-2 px-2 py-1.5 sm:px-3 sm:py-2 min-w-[60px] sm:min-w-[80px]
                min-h-[68px] sm:min-h-[76px]
                transition-all duration-500
                ${agent.status === "running" ? "border-[hsl(45,93%,47%)]" : ""}
                ${agent.status === "completed" ? "border-border" : ""}
                ${agent.status === "idle" ? "border-border opacity-40" : ""}
                ${agent.status === "running" ? "bg-secondary" : ""}
                ${agent.status === "completed" ? "bg-secondary/50" : ""}
              `}
            >
              {/* Active pulse indicator */}
              {agent.status === "running" && (
                <span className="absolute -top-1 -right-1 flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full opacity-75 bg-[hsl(45,93%,47%)]"></span>
                  <span className="relative inline-flex h-2.5 w-2.5 bg-[hsl(45,93%,47%)]"></span>
                </span>
              )}

              {/* Status icon */}
              <span className="inline-flex items-center justify-center w-5 h-5 text-sm">
                {agent.status === "completed" ? "\u2713" : agent.status === "running" ? "\u25CB" : "\u25CB"}
              </span>

              <span className="text-[9px] sm:text-[10px] font-medium">
                {AGENT_LABELS[agent.name]}
              </span>

              <span className={`text-[9px] mt-0.5 ${agent.durationSeconds !== null ? "text-muted-foreground" : "invisible"}`}>
                {agent.durationSeconds !== null ? `${agent.durationSeconds.toFixed(1)}s` : "0s"}
              </span>
            </div>

            {/* Arrow connector */}
            {i < agents.length - 1 && (() => {
              const next = agents[i + 1];
              const bothCompleted = agent.status === "completed" && next.status === "completed";
              const completedToRunning = agent.status === "completed" && next.status === "running";
              const arrowColor = bothCompleted
                ? "hsl(142, 76%, 36%)"
                : completedToRunning
                  ? "hsl(45, 93%, 47%)"
                  : "hsl(215, 20.2%, 65.1%)";
              return (
                <div className="flex-shrink-0 rotate-90 sm:rotate-0">
                  <svg width="20" height="10" viewBox="0 0 24 12" className={bothCompleted || completedToRunning ? "" : "opacity-40"}>
                    <path d="M0 6h16m0 0l-4-4m4 4l-4 4" stroke={arrowColor} strokeWidth="1.5" fill="none" />
                  </svg>
                </div>
              );
            })()}
          </div>
        ))}
      </div>
    </div>
  );
}
