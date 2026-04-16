"use client";

import React, { createContext, useCallback, useContext, useState } from "react";
import { startAnalysis, getResults } from "@/lib/api";
import type { AnalysisPhase, HypothesisOutput, ResultResponse } from "@/lib/types";

interface AnalysisContextValue {
  runId: string | null;
  phase: AnalysisPhase;
  hypothesis: HypothesisOutput | null;
  reportContent: string | null;
  error: string | null;
  submit: (query: string, mode: "test" | "live") => Promise<string | null>;
  fetchResults: () => Promise<void>;
  reset: () => void;
}

const AnalysisContext = createContext<AnalysisContextValue>({
  runId: null,
  phase: "idle",
  hypothesis: null,
  reportContent: null,
  error: null,
  submit: async () => null,
  fetchResults: async () => {},
  reset: () => {},
});

export function AnalysisProvider({ children }: { children: React.ReactNode }) {
  const [runId, setRunId] = useState<string | null>(null);
  const [phase, setPhase] = useState<AnalysisPhase>("idle");
  const [hypothesis, setHypothesis] = useState<HypothesisOutput | null>(null);
  const [reportContent, setReportContent] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(async (query: string, mode: "test" | "live") => {
    setPhase("submitting");
    setError(null);
    setHypothesis(null);
    setReportContent(null);

    try {
      const response = await startAnalysis({ query, mode });
      setRunId(response.run_id);
      setPhase("running");
      return response.run_id;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to start analysis";
      setError(message);
      setPhase("failed");
      return null;
    }
  }, []);

  const fetchResults = useCallback(async () => {
    if (!runId) return;

    try {
      const results: ResultResponse = await getResults(runId);
      if (results.hypothesis) {
        setHypothesis(results.hypothesis);
      }
      if (results.report_content) {
        setReportContent(results.report_content);
      }
      if (results.error) {
        setError(results.error);
      }
      setPhase("completed");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to fetch results";
      setError(message);
      setPhase("failed");
    }
  }, [runId]);

  const reset = useCallback(() => {
    setRunId(null);
    setPhase("idle");
    setHypothesis(null);
    setReportContent(null);
    setError(null);
  }, []);

  return (
    <AnalysisContext.Provider
      value={{ runId, phase, hypothesis, reportContent, error, submit, fetchResults, reset }}
    >
      {children}
    </AnalysisContext.Provider>
  );
}

export function useAnalysis() {
  return useContext(AnalysisContext);
}
