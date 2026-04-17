"use client";

import React, {
  createContext,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { WebSocketClient } from "@/lib/websocket";
import { getWebSocketUrl } from "@/lib/api";
import type {
  AgentName,
  AgentProgress,
  AgentState,
  AgentStatus,
  AnalysisPhase,
  ClassificationEDAResult,
  ClusteringEDAResult,
  HypothesisOutput,
  LogEntry,
  RateLimitStatus,
  WSMessageType,
} from "@/lib/types";

const INITIAL_AGENTS: AgentState[] = [
  { name: "orchestrator", status: "idle", startedAt: null, completedAt: null, durationSeconds: null },
  { name: "analyst", status: "idle", startedAt: null, completedAt: null, durationSeconds: null },
  { name: "hypothesis", status: "idle", startedAt: null, completedAt: null, durationSeconds: null },
];

export type ConnectionStatus = "disconnected" | "connecting" | "connected" | "error";

interface WebSocketContextValue {
  runId: string | null;
  phase: AnalysisPhase;
  agents: AgentState[];
  logs: LogEntry[];
  rateLimit: RateLimitStatus | null;
  error: string | null;
  finalResponse: string | null;
  currentActivity: string | null;
  progressPercent: number;
  connectionStatus: ConnectionStatus;
  classificationEDA: ClassificationEDAResult | null;
  clusteringEDA: ClusteringEDAResult | null;
  hypothesis: HypothesisOutput | null;
  agentProgress: AgentProgress | null;
  elapsed: number;
  connect: (runId: string) => void;
  cancelAnalysis: () => void;
  reset: () => void;
}

export const WebSocketContext = createContext<WebSocketContextValue>({
  runId: null,
  phase: "idle",
  agents: INITIAL_AGENTS,
  logs: [],
  rateLimit: null,
  error: null,
  finalResponse: null,
  currentActivity: null,
  progressPercent: 0,
  connectionStatus: "disconnected",
  classificationEDA: null,
  clusteringEDA: null,
  hypothesis: null,
  agentProgress: null,
  elapsed: 0,
  connect: () => {},
  cancelAnalysis: () => {},
  reset: () => {},
});

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const clientRef = useRef<WebSocketClient | null>(null);

  const [runId, setRunId] = useState<string | null>(null);
  const [phase, setPhase] = useState<AnalysisPhase>("idle");
  const [agents, setAgents] = useState<AgentState[]>(INITIAL_AGENTS);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [rateLimit, setRateLimit] = useState<RateLimitStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [finalResponse, setFinalResponse] = useState<string | null>(null);
  const [currentActivity, setCurrentActivity] = useState<string | null>(null);
  const [progressPercent, setProgressPercent] = useState<number>(0);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("disconnected");
  const [classificationEDA, setClassificationEDA] = useState<ClassificationEDAResult | null>(null);
  const [clusteringEDA, setClusteringEDA] = useState<ClusteringEDAResult | null>(null);
  const [hypothesis, setHypothesis] = useState<HypothesisOutput | null>(null);
  const [agentProgress, setAgentProgress] = useState<AgentProgress | null>(null);
  const [elapsed, setElapsed] = useState<number>(0);
  const [elapsedStartTime, setElapsedStartTime] = useState<number | null>(null);

  // Elapsed timer: counts seconds while phase === "running"
  useEffect(() => {
    if (phase !== "running") {
      setElapsed(0);
      setElapsedStartTime(null);
      return;
    }
    if (elapsedStartTime === null) {
      setElapsedStartTime(Date.now());
    }
    const interval = setInterval(() => {
      setElapsed((prev) => {
        if (elapsedStartTime) {
          return Math.floor((Date.now() - elapsedStartTime) / 1000);
        }
        return prev + 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [phase, elapsedStartTime]);

  const WS_RUN_ID_STORAGE_KEY = "ws_run_id";

  // Restore runId from sessionStorage on mount (survives page refresh)
  useEffect(() => {
    const savedRunId = sessionStorage.getItem(WS_RUN_ID_STORAGE_KEY);
    if (savedRunId) {
      setRunId(savedRunId);
      setPhase("completed");
      setProgressPercent(100);
    }
  }, []);

  const handleMessage = useCallback((message: WSMessageType) => {
    switch (message.type) {
      case "connected":
        setConnectionStatus("connected");
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
          orchestrator: "Collector (fetch posts)",
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
        setAgentProgress({ agent_name, tool_name, progress });
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
        setConnectionStatus("error");
        setError(data.message);
        setPhase("failed");
        setCurrentActivity(`Error: ${data.message}`);
        break;
      }

      case "intermediary_result": {
        const { result_type, data: edaData } = message.data as {
          result_type: "classification_eda" | "clustering_eda" | "hypothesis";
          data: Record<string, unknown>;
        };
        if (result_type === "classification_eda") {
          setClassificationEDA(edaData as unknown as ClassificationEDAResult);
        } else if (result_type === "clustering_eda") {
          setClusteringEDA(edaData as unknown as ClusteringEDAResult);
        } else if (result_type === "hypothesis") {
          setHypothesis(edaData as unknown as HypothesisOutput);
        }
        break;
      }
    }
  }, []);

  const connect = useCallback((newRunId: string) => {
    // Close existing connection if any
    if (clientRef.current) {
      clientRef.current.markReplaced();
      clientRef.current.close();
    }

    setRunId(newRunId);
    sessionStorage.setItem(WS_RUN_ID_STORAGE_KEY, newRunId);
    setPhase("running");
    setConnectionStatus("connecting");
    setAgents(INITIAL_AGENTS);
    setLogs([]);
    setError(null);
    setFinalResponse(null);
    setCurrentActivity("Connecting...");
    setProgressPercent(2);
    setClassificationEDA(null);
    setClusteringEDA(null);
    setHypothesis(null);
    setAgentProgress(null);
    setElapsed(0);
    setElapsedStartTime(Date.now());

    const url = getWebSocketUrl(newRunId);
    const client = new WebSocketClient(url, handleMessage);
    clientRef.current = client;
    client.connect();
  }, [handleMessage]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (clientRef.current) {
        clientRef.current.close();
        clientRef.current = null;
      }
    };
  }, []);

  const cancelAnalysis = useCallback(() => {
    clientRef.current?.send({ type: "cancel_analysis", data: { run_id: runId } });
  }, [runId]);

  const reset = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.markReplaced();
      clientRef.current.close();
      clientRef.current = null;
    }
    setRunId(null);
    sessionStorage.removeItem(WS_RUN_ID_STORAGE_KEY);
    setPhase("idle");
    setAgents(INITIAL_AGENTS);
    setLogs([]);
    setRateLimit(null);
    setError(null);
    setFinalResponse(null);
    setCurrentActivity(null);
    setProgressPercent(0);
    setConnectionStatus("disconnected");
    setClassificationEDA(null);
    setClusteringEDA(null);
    setHypothesis(null);
    setAgentProgress(null);
    setElapsed(0);
    setElapsedStartTime(null);
  }, []);

  return (
    <WebSocketContext.Provider
      value={{
        runId,
        phase,
        agents,
        logs,
        rateLimit,
        error,
        finalResponse,
        currentActivity,
        progressPercent,
        connectionStatus,
        classificationEDA,
        clusteringEDA,
        hypothesis,
        agentProgress,
        elapsed,
        connect,
        cancelAnalysis,
        reset,
      }}
    >
      {children}
    </WebSocketContext.Provider>
  );
}
