"use client";

import { useState, useEffect } from "react";
import type { AgentState } from "@/lib/types";

const DISPLAY_NAMES: Record<string, string> = {
  orchestrator: "Fetching posts",
  analyst: "Analyzing data",
  hypothesis: "Generating report",
};

export interface QueueItem {
  id: string;
  name: string;
  status: "waiting" | "sent" | "error";
  elapsed: number;
}

export function useRequestQueue(agents: AgentState[]): QueueItem[] {
  const [now, setNow] = useState(Date.now());

  // Tick every second to update elapsed times
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  return agents
    .filter((a) => a.status !== "idle")
    .map((agent) => ({
      id: agent.name,
      name: DISPLAY_NAMES[agent.name] || agent.name,
      status:
        agent.status === "completed"
          ? "sent" as const
          : agent.status === "error"
          ? "error" as const
          : "waiting" as const,
      elapsed: agent.startedAt ? Math.round((now - agent.startedAt) / 1000) : 0,
    }));
}
