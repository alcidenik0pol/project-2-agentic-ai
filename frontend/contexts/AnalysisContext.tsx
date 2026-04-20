"use client";

import React, { createContext, useCallback, useContext, useState } from "react";
import { startAnalysis, getResults } from "@/lib/api";
import type { AnalysisPhase, ResultResponse } from "@/lib/types";

interface AnalysisContextValue {
  runId: string | null;
  phase: AnalysisPhase;
  reportContent: string | null;
  error: string | null;
  submit: (query: string, mode: "test" | "live") => Promise<string | null>;
  fetchResults: (overrideRunId?: string) => Promise<ResultResponse | null>;
  reset: () => void;
}

const AnalysisContext = createContext<AnalysisContextValue>({
  runId: null,
  phase: "idle",
  reportContent: null,
  error: null,
  submit: async () => null,
  fetchResults: async () => null,
  reset: () => {},
});

export function AnalysisProvider({ children }: { children: React.ReactNode }) {
  const [runId, setRunId] = useState<string | null>(null);
  const [phase, setPhase] = useState<AnalysisPhase>("idle");
  const [reportContent, setReportContent] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(async (query: string, mode: "test" | "live") => {
    console.log("[Analysis] submit() called", { query, mode });
    setPhase("submitting");
    setError(null);
    setReportContent(null);

    try {
      console.log("[Analysis] submit: calling startAnalysis API...");
      const response = await startAnalysis({ query, mode });
      console.log("[Analysis] submit: API response received", { run_id: response.run_id });
      setRunId(response.run_id);
      setPhase("running");
      return response.run_id;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to start analysis";
      console.error("[Analysis] submit: API call failed", {
        error: message,
        errorType: err instanceof Error ? err.constructor.name : typeof err,
        query,
        mode,
      });
      setError(message);
      setPhase("failed");
      return null;
    }
  }, []);

  const fetchResults = useCallback(async (overrideRunId?: string): Promise<ResultResponse | null> => {
    const id = overrideRunId ?? runId;
    console.log("[Analysis] fetchResults called", { overrideRunId, resolvedId: id, storedRunId: runId });
    if (!id) {
      console.warn("[Analysis] fetchResults: no runId available, returning null");
      return null;
    }

    try {
      console.log(`[Analysis] fetchResults: calling getResults(${id})...`);
      const results: ResultResponse = await getResults(id);
      console.log("[Analysis] fetchResults: results received", {
        hasReport: !!results.report_content,
        hasError: !!results.error,
        status: results.status,
        hasHypothesis: !!results.hypothesis,
      });
      if (results.report_content) {
        setReportContent(results.report_content);
      }
      if (results.error) {
        setError(results.error);
      }
      setPhase("completed");
      return results;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to fetch results";
      console.error("[Analysis] fetchResults: failed", {
        error: message,
        errorType: err instanceof Error ? err.constructor.name : typeof err,
        runId: id,
      });
      if (message.includes("404")) {
        console.log("[Analysis] fetchResults: 404 — clearing run, returning to idle");
        setRunId(null);
        setPhase("idle");
        setReportContent(null);
        setError(null);
      } else {
        setError(message);
        setPhase("failed");
      }
      return null;
    }
  }, [runId]);

  const reset = useCallback(() => {
    console.log("[Analysis] reset() called", { currentRunId: runId, currentPhase: phase });
    setRunId(null);
    setPhase("idle");
    setReportContent(null);
    setError(null);
  }, [runId, phase]);

  return (
    <AnalysisContext.Provider
      value={{ runId, phase, reportContent, error, submit, fetchResults, reset }}
    >
      {children}
    </AnalysisContext.Provider>
  );
}

export function useAnalysis() {
  return useContext(AnalysisContext);
}
