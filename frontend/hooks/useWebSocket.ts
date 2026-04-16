"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { WebSocketClient } from "@/lib/websocket";
import { getWebSocketUrl } from "@/lib/api";
import type {
  AgentName,
  AgentState,
  AgentStatus,
  AnalysisPhase,
  LogEntry,
  RateLimitStatus,
  WSMessageType,
} from "@/lib/types";

const INITIAL_AGENTS: AgentState[] = [
  { name: "subreddit_selector", status: "idle", startedAt: null, completedAt: null, durationSeconds: null },
  { name: "orchestrator", status: "idle", startedAt: null, completedAt: null, durationSeconds: null },
  { name: "analyst", status: "idle", startedAt: null, completedAt: null, durationSeconds: null },
  { name: "hypothesis", status: "idle", startedAt: null, completedAt: null, durationSeconds: null },
];

export function useWebSocket(runId: string | null) {
  const clientRef = useRef<WebSocketClient | null>(null);

  const [phase, setPhase] = useState<AnalysisPhase>("idle");
  const [agents, setAgents] = useState<AgentState[]>(INITIAL_AGENTS);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [rateLimit, setRateLimit] = useState<RateLimitStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [finalResponse, setFinalResponse] = useState<string | null>(null);
  const [currentActivity, setCurrentActivity] = useState<string | null>(null);
  const [progressPercent, setProgressPercent] = useState<number>(0);

  const handleMessage = useCallback((message: WSMessageType) => {
    switch (message.type) {
      case "connected":
        setPhase("running");
        setProgressPercent(5);
        setCurrentActivity("Connected to server, starting pipeline...");
        break;

      case "agent_started": {
        const { agent_name, iteration, max_iterations } = message.data as {
          agent_name: AgentName;
          iteration: number;
          max_iterations: number;
        };
        setAgents((prev) =>
          prev.map((a) =>
            a.name === agent_name
              ? { ...a, status: "running" as AgentStatus, startedAt: Date.now() }
              : a
          )
        );
        const pct = Math.round((iteration / max_iterations) * 100) * 0.3 + 10;
        setProgressPercent(Math.min(pct, 95));
        const agentLabels: Record<string, string> = {
          subreddit_selector: "Selecting Subreddits",
          orchestrator: "Orchestrator (fetch_posts)",
          analyst: "Analyst (classify, cluster)",
          hypothesis: "Hypothesis (generate, save)",
        };
        setCurrentActivity(`Agent: ${agentLabels[agent_name] || agent_name}`);
        break;
      }

      case "agent_completed": {
        const { agent_name, duration_seconds } = message.data as {
          agent_name: AgentName;
          duration_seconds: number;
        };
        setAgents((prev) =>
          prev.map((a) =>
            a.name === agent_name
              ? { ...a, status: "completed" as AgentStatus, completedAt: Date.now(), durationSeconds: duration_seconds }
              : a
          )
        );
        break;
      }

      case "agent_progress": {
        const { agent_name, tool_name, progress } = message.data as {
          agent_name: AgentName;
          tool_name: string;
          progress: { current: number; total: number; percentage: number };
        };
        setCurrentActivity(`${tool_name}: ${progress.current}/${progress.total}`);
        setProgressPercent(Math.min(progress.percentage, 95));
        break;
      }

      case "rate_limit_update": {
        setRateLimit(message.data as unknown as RateLimitStatus);
        break;
      }

      case "log_entry": {
        const logData = message.data as {
          level: "INFO" | "WARNING" | "ERROR";
          logger: string;
          message: string;
          agent_name?: AgentName;
        };
        const entry: LogEntry = {
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          level: logData.level,
          logger: logData.logger,
          message: logData.message,
          agent_name: logData.agent_name,
          timestamp: Date.now(),
        };
        setLogs((prev) => [...prev, entry]);
        break;
      }

      case "analysis_complete": {
        const data = message.data as { final_response: string };
        setFinalResponse(data.final_response);
        setPhase("completed");
        setProgressPercent(100);
        setCurrentActivity("Found something.");
        break;
      }

      case "error": {
        const data = message.data as { message: string };
        setError(data.message);
        setPhase("failed");
        setCurrentActivity(`Error: ${data.message}`);
        break;
      }
    }
  }, []);

  useEffect(() => {
    if (!runId) return;

    const url = getWebSocketUrl(runId);
    const client = new WebSocketClient(url, handleMessage);
    clientRef.current = client;
    client.connect();

    return () => {
      client.close();
      clientRef.current = null;
    };
  }, [runId, handleMessage]);

  const cancelAnalysis = useCallback(() => {
    clientRef.current?.send({ type: "cancel_analysis", data: { run_id: runId } });
  }, [runId]);

  const reset = useCallback(() => {
    setPhase("idle");
    setAgents(INITIAL_AGENTS);
    setLogs([]);
    setRateLimit(null);
    setError(null);
    setFinalResponse(null);
    setCurrentActivity(null);
    setProgressPercent(0);
  }, []);

  return {
    phase,
    agents,
    logs,
    rateLimit,
    error,
    finalResponse,
    currentActivity,
    progressPercent,
    cancelAnalysis,
    reset,
    setPhase,
  };
}
