/**
 * REST API client for the backend.
 */

import type {
  AnalysisRequest,
  AnalysisResponse,
  HealthResponse,
  RateLimitStatus,
  ResultResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ||
  (process.env.NODE_ENV === 'development' ? '' : 'http://localhost:8901');

/**
 * Custom error for when usage limit is exceeded (429).
 */
export class UsageLimitExceededError extends Error {
  resetsAt: string;
  used: number;
  limit: number;

  constructor(data: { resets_at: string; used: number; limit: number }) {
    super("Monthly usage limit exceeded");
    this.name = "UsageLimitExceededError";
    this.resetsAt = data.resets_at;
    this.used = data.used;
    this.limit = data.limit;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}/api/v1${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    // Special handling for 429 (usage limit exceeded)
    if (res.status === 429) {
      try {
        const data = await res.json();
        if (data.error === "usage_limit_exceeded") {
          throw new UsageLimitExceededError({
            resets_at: data.resets_at,
            used: data.used,
            limit: data.limit,
          });
        }
      } catch (e) {
        if (e instanceof UsageLimitExceededError) throw e;
      }
    }
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }

  return res.json();
}

export async function startAnalysis(req: AnalysisRequest): Promise<AnalysisResponse> {
  return request<AnalysisResponse>("/analysis", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export async function getResults(runId: string): Promise<ResultResponse> {
  return request<ResultResponse>(`/results/${runId}`);
}

export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export async function getRateLimit(): Promise<RateLimitStatus> {
  return request<RateLimitStatus>("/rate-limit");
}

export function getFileUrl(runId: string, filename: string): string {
  return `${API_BASE}/api/v1/results/${runId}/file/${filename}`;
}

export function getZipUrl(runId: string): string {
  return `${API_BASE}/api/v1/results/${runId}/zip`;
}

export function getWebSocketUrl(runId: string): string {
  // If API_BASE is configured, derive WebSocket URL from it
  if (API_BASE) {
    const base = API_BASE.replace(/^http/, "ws");
    return `${base}/ws/${runId}`;
  }

  // API_BASE is empty (using Next.js rewrites for REST).
  // WebSocket can't be proxied through Next.js rewrites, so connect directly to backend.
  if (typeof window !== "undefined") {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    // In development the frontend runs on port 3456, backend on 8901
    const backendPort = window.location.port === "3456" || window.location.port === "3000"
      ? "8901"
      : window.location.port;
    return `${protocol}//${window.location.hostname}:${backendPort}/ws/${runId}`;
  }

  // SSR fallback
  return `ws://127.0.0.1:8901/ws/${runId}`;
}
