"use client";

import { useCallback, useState } from "react";
import { startAnalysis, getResults } from "@/lib/api";
import type { AnalysisPhase, HypothesisOutput, ResultResponse } from "@/lib/types";

export function useAnalysis() {
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
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to fetch results";
      setError(message);
    }
  }, [runId]);

  const reset = useCallback(() => {
    setRunId(null);
    setPhase("idle");
    setHypothesis(null);
    setReportContent(null);
    setError(null);
  }, []);

  return {
    runId,
    phase,
    hypothesis,
    reportContent,
    error,
    submit,
    fetchResults,
    setPhase,
    reset,
  };
}
