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
  ConnectionLostMessage,
  HypothesisOutput,
  LogEntry,
  RateLimitStatus,
  ResultResponse,
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
  connect: (runId: string, isRecovery?: boolean) => void;
  cancelAnalysis: () => void;
  reset: () => void;
  prepareNewRun: () => void;
  recoverResults: (results: ResultResponse) => void;
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
  prepareNewRun: () => {},
  recoverResults: () => {},
});

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const clientRef = useRef<WebSocketClient | null>(null);
  const runIdRef = useRef<string | null>(null);

  const [runId, setRunId] = useState<string | null>(null);
  const [phase, setPhase] = useState<AnalysisPhase>("idle");
  const phaseRef = useRef<AnalysisPhase>("idle");
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

  // Keep phaseRef in sync so handleMessage (stable callback) can read current phase
  const updatePhase = useCallback((newPhase: AnalysisPhase) => {
    phaseRef.current = newPhase;
    setPhase(newPhase);
  }, []);

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

  const handleMessage = useCallback((message: WSMessageType) => {
    // Ignore messages for stale run_ids (e.g., from previous runs or buffered connections)
    const messageRunId = (message.data as { run_id?: string })?.run_id;
    if (runIdRef.current && messageRunId && messageRunId !== runIdRef.current) {
      console.warn(
        `[WSContext] Ignoring message for stale run_id: ${messageRunId} (current: ${runIdRef.current}), type=${message.type}`
      );
      return;
    }

    console.log(`[WSContext] handleMessage: type=${message.type}`, {
      currentRunId: runIdRef.current,
      messageRunId: messageRunId || "(none)",
      currentPhase: phaseRef.current,
      data: message.data,
    });

    switch (message.type) {
      case "connected":
        console.log("[WSContext] Connected — setting phase=running");
        setConnectionStatus("connected");
        updatePhase("running");
        setProgressPercent(5);
        setCurrentActivity("Connected to server, starting pipeline...");
        break;

      case "agent_started": {
        const { agent_name, iteration, max_iterations } = message.data as {
          agent_name: AgentName;
          iteration: number;
          max_iterations: number;
        };
        console.log(`[WSContext] Agent started: ${agent_name}`, { iteration, max_iterations });
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
        console.log(`[WSContext] Agent completed: ${agent_name}`, { duration_seconds });
        setAgents((prev) =>
          prev.map((a) =>
            a.name === agent_name
              ? { ...a, status: "completed" as AgentStatus, completedAt: Date.now(), durationSeconds: duration_seconds }
              : a
          )
        );
        break;
      }

      case "analysis_cancelled": {
        const data = message.data as { message: string };
        console.log("[WSContext] Analysis cancelled:", data.message);
        setConnectionStatus("disconnected");
        setError(data.message);
        updatePhase("idle");
        setProgressPercent(0);
        setCurrentActivity("Cancelled");
        break;
      }

      case "agent_progress": {
        const { agent_name, tool_name, progress } = message.data as {
          agent_name: AgentName;
          tool_name: string;
          progress: { current: number; total: number; percentage: number };
        };
        console.log(`[WSContext] Agent progress: ${agent_name}/${tool_name}`, progress);
        setAgentProgress({ agent_name, tool_name, progress });
        setCurrentActivity(`${tool_name}: ${progress.current}/${progress.total}`);
        setProgressPercent(Math.min(progress.percentage, 95));
        break;
      }

      case "rate_limit_update": {
        console.log("[WSContext] Rate limit update:", message.data);
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
        console.log(`[WSContext] Log entry [${logData.level}] ${logData.logger}: ${logData.message}`);
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
        console.log("[WSContext] Analysis complete — setting phase=completed");
        setFinalResponse(data.final_response);
        updatePhase("completed");
        setProgressPercent(100);
        setCurrentActivity("Found something.");
        break;
      }

      case "error": {
        const data = message.data as { message: string };
        console.error("[WSContext] Error message from server:", data.message);
        setConnectionStatus("error");
        setError(data.message);
        updatePhase("failed");
        setCurrentActivity(`Error: ${data.message}`);
        break;
      }

      case "connection_lost": {
        const data = (message as ConnectionLostMessage).data;
        console.warn("[WSContext] Connection lost:", {
          message: data.message,
          currentPhase: phaseRef.current,
          willShowError: phaseRef.current !== "completed" && phaseRef.current !== "failed",
        });
        if (phaseRef.current !== "completed" && phaseRef.current !== "failed") {
          setConnectionStatus("error");
          setError(data.message);
          updatePhase("failed");
          setCurrentActivity(`Connection lost: ${data.message}`);
        }
        break;
      }

      case "intermediary_result": {
        const { result_type, data: edaData } = message.data as {
          result_type: "classification_eda" | "clustering_eda" | "hypothesis";
          data: Record<string, unknown>;
        };
        console.log(`[WSContext] Intermediary result: ${result_type}`);
        if (result_type === "classification_eda") {
          setClassificationEDA(edaData as unknown as ClassificationEDAResult);
        } else if (result_type === "clustering_eda") {
          setClusteringEDA(edaData as unknown as ClusteringEDAResult);
        } else if (result_type === "hypothesis") {
          setHypothesis(edaData as unknown as HypothesisOutput);
        }
        break;
      }

      default:
        console.warn("[WSContext] Unknown message type:", (message as { type: string }).type, message.data);
    }
  }, [updatePhase]);

  const connect = useCallback((newRunId: string, isRecovery?: boolean) => {
    console.log(`[WSContext] connect() called`, {
      newRunId,
      isRecovery: isRecovery ?? false,
      hadExistingClient: !!clientRef.current,
      previousRunId: runIdRef.current,
    });

    // Close existing connection if any
    if (clientRef.current) {
      console.log("[WSContext] connect: closing existing client");
      clientRef.current.markReplaced();
      clientRef.current.close();
    }

    setRunId(newRunId);
    runIdRef.current = newRunId;
    setConnectionStatus("connecting");

    if (!isRecovery) {
      // Full reset for new runs
      console.log("[WSContext] connect: full reset for new run");
      updatePhase("running");
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
    } else {
      // Recovery mode — restore running state without clearing existing data
      console.log("[WSContext] connect: recovery mode — reconnecting");
      updatePhase("running");
      setCurrentActivity("Reconnecting to analysis...");
      setProgressPercent(5);
    }

    const url = getWebSocketUrl(newRunId);
    console.log(`[WSContext] connect: creating WebSocketClient, url=${url}`);
    const client = new WebSocketClient(url, handleMessage);
    clientRef.current = client;
    client.connect();
    console.log(`[WSContext] connect: WebSocketClient.connect() called for run ${newRunId}`);
  }, [handleMessage, updatePhase]);

  // Persist state to localStorage for recovery after page refresh
  useEffect(() => {
    if (runId && phase === "running") {
      localStorage.setItem("analysis_run_id", runId);
      localStorage.setItem("analysis_phase", phase);
      localStorage.setItem("analysis_timestamp", Date.now().toString());
    } else if (phase === "completed" || phase === "failed") {
      localStorage.removeItem("analysis_run_id");
      localStorage.removeItem("analysis_phase");
      localStorage.removeItem("analysis_timestamp");
    }
  }, [runId, phase]);

  // Recovery: check localStorage on mount for a running analysis
  useEffect(() => {
    const savedRunId = localStorage.getItem("analysis_run_id");
    const savedPhase = localStorage.getItem("analysis_phase");
    const savedTimestamp = localStorage.getItem("analysis_timestamp");

    if (savedRunId && savedPhase === "running") {
      const elapsed = Date.now() - parseInt(savedTimestamp || "0");
      if (elapsed < 15 * 60 * 1000) { // 15 minutes
        console.log("[WebSocket] Attempting recovery for run:", savedRunId);
        connect(savedRunId, true);
      } else {
        // Clear stale data
        localStorage.removeItem("analysis_run_id");
        localStorage.removeItem("analysis_phase");
        localStorage.removeItem("analysis_timestamp");
      }
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps -- intentional: run once on mount

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
    console.log("[WSContext] cancelAnalysis called", {
      runId,
      hasClient: !!clientRef.current,
      clientConnected: clientRef.current?.isConnected,
    });
    clientRef.current?.send({ type: "cancel_analysis", data: { run_id: runId } });
  }, [runId]);

  const reset = useCallback(() => {
    console.log("[WSContext] reset() called", {
      currentRunId: runIdRef.current,
      hasClient: !!clientRef.current,
      currentPhase: phaseRef.current,
    });

    if (clientRef.current) {
      console.log("[WSContext] reset: closing and nulling client");
      clientRef.current.markReplaced();
      clientRef.current.close();
      clientRef.current = null;
    }
    setRunId(null);
    runIdRef.current = null;
    updatePhase("idle");
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

    // Clear localStorage recovery state so page refresh doesn't
    // attempt to recover a manually-reset analysis
    localStorage.removeItem("analysis_run_id");
    localStorage.removeItem("analysis_phase");
    localStorage.removeItem("analysis_timestamp");
    console.log("[WSContext] reset() complete — all state cleared");
  }, [updatePhase]);

  const prepareNewRun = useCallback(() => {
    console.log("[WSContext] prepareNewRun() called", {
      currentRunId: runIdRef.current,
      hasClient: !!clientRef.current,
      currentPhase: phaseRef.current,
    });

    // Close old connection immediately to prevent stale message interference
    // during the submit() → connect() gap.
    if (clientRef.current) {
      console.log("[WSContext] prepareNewRun: closing old client to prevent stale messages");
      clientRef.current.markReplaced();
      clientRef.current.close();
      clientRef.current = null;
    }

    // Reset all WS UI state for a new run.
    setRunId(null);
    runIdRef.current = null;
    updatePhase("idle");
    setAgents(INITIAL_AGENTS);
    setLogs([]);
    setRateLimit(null);
    setError(null);
    setFinalResponse(null);
    setCurrentActivity(null);
    setProgressPercent(0);
    setClassificationEDA(null);
    setClusteringEDA(null);
    setHypothesis(null);
    setAgentProgress(null);
    setElapsed(0);
    setElapsedStartTime(null);
    console.log("[WSContext] prepareNewRun() complete — ready for new submission");
  }, [updatePhase]);

  const recoverResults = useCallback((results: ResultResponse) => {
    console.log("[WSContext] recoverResults called", {
      hasHypothesis: !!results.hypothesis,
      hasClassification: !!results.classification_eda,
      hasClustering: !!results.clustering_eda,
      status: results.status,
    });
    if (results.hypothesis) setHypothesis(results.hypothesis);
    if (results.classification_eda) setClassificationEDA(results.classification_eda);
    if (results.clustering_eda) setClusteringEDA(results.clustering_eda);
    if (results.status === "completed") {
      updatePhase("completed");
      setProgressPercent(100);
      setCurrentActivity("Recovered from saved results");
      setAgents(INITIAL_AGENTS.map(a => ({ ...a, status: "completed" as AgentStatus })));
    }
  }, [updatePhase]);

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
        prepareNewRun,
        recoverResults,
      }}
    >
      {children}
    </WebSocketContext.Provider>
  );
}
