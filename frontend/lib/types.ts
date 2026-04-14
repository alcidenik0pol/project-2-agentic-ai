// TypeScript types matching backend Pydantic models

// ── WebSocket Messages ──

export interface WSMessage {
  type: string;
  data: Record<string, unknown>;
}

export interface ConnectedMessage {
  type: "connected";
  data: { run_id: string; server_time: string };
}

export interface AgentStartedMessage {
  type: "agent_started";
  data: { agent_name: AgentName; iteration: number; max_iterations: number };
}

export interface AgentCompletedMessage {
  type: "agent_completed";
  data: { agent_name: AgentName; duration_seconds: number };
}

export interface AgentProgressMessage {
  type: "agent_progress";
  data: {
    agent_name: AgentName;
    tool_name: string;
    progress: { current: number; total: number; percentage: number };
  };
}

export interface RateLimitUpdateMessage {
  type: "rate_limit_update";
  data: RateLimitStatus;
}

export interface LogEntryMessage {
  type: "log_entry";
  data: {
    level: "INFO" | "WARNING" | "ERROR";
    logger: string;
    message: string;
    agent_name?: AgentName;
  };
}

export interface AnalysisCompleteMessage {
  type: "analysis_complete";
  data: {
    run_id: string;
    final_response: string;
    results: { hypothesis_path: string; report_path: string };
  };
}

export interface ErrorMessage {
  type: "error";
  data: { message: string };
}

export type WSMessageType =
  | ConnectedMessage
  | AgentStartedMessage
  | AgentCompletedMessage
  | AgentProgressMessage
  | RateLimitUpdateMessage
  | LogEntryMessage
  | AnalysisCompleteMessage
  | ErrorMessage;

// ── Agent Types ──

export type AgentName = "subreddit_selector" | "orchestrator" | "analyst" | "hypothesis";

export type AgentStatus = "idle" | "running" | "completed" | "error";

export interface AgentState {
  name: AgentName;
  status: AgentStatus;
  startedAt: number | null;
  completedAt: number | null;
  durationSeconds: number | null;
}

// ── REST API Types ──

export interface AnalysisRequest {
  query: string;
  mode: "test" | "live";
}

export interface AnalysisResponse {
  run_id: string;
  websocket_url: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  llm_provider: string;
  agent_mode: string;
}

export interface RateLimitStatus {
  requests_in_window: number;
  requests_remaining: number;
  seconds_until_reset: number;
  is_throttled: boolean;
  limit: number;
}

export interface HypothesisEvidence {
  cluster_name: string;
  post_count: number;
  total_upvotes: number;
  supporting_post_titles: string[];
}

export interface BusinessIdea {
  rank: number;
  idea_name: string;
  pain_point: string;
  solution_description: string;
  core_features?: string;
  revenue_model?: string;
  first_user_step?: string;
  target_user: string;
  evidence: HypothesisEvidence;
  confidence: "high" | "medium" | "low";
  confidence_reasoning: string;
}

export interface HypothesisOutput {
  ideas: BusinessIdea[];
  analysis_summary: string;
  data_limitations: string;
  source_cluster_count: number;
  processing_time_seconds: number;
  model_used: string;
  generated_at: string | null;
}

export interface ResultResponse {
  run_id: string;
  status: "completed" | "failed" | "running";
  hypothesis: HypothesisOutput | null;
  report_content: string | null;
  agent_results: Record<string, unknown> | null;
  error: string | null;
}

// ── App State ──

export type AnalysisPhase = "idle" | "submitting" | "running" | "completed" | "failed";

export interface LogEntry {
  id: string;
  level: "INFO" | "WARNING" | "ERROR";
  logger: string;
  message: string;
  agent_name?: AgentName;
  timestamp: number;
}
