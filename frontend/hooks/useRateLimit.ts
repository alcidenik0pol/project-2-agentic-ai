"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { getRateLimit } from "@/lib/api";
import type { RateLimitStatus } from "@/lib/types";

interface UseRateLimitReturn {
  rateLimit: RateLimitStatus | null;
  countdown: number;
  isLoading: boolean;
  error: string | null;
}

const POLL_INTERVAL_MS = 2000;

export function useRateLimit(): UseRateLimitReturn {
  const [rateLimit, setRateLimit] = useState<RateLimitStatus | null>(null);
  const [countdown, setCountdown] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const lastApiCountdown = useRef<number>(0);
  const lastFetchTime = useRef<number>(Date.now());

  // Fetch rate limit from REST API
  const fetchRateLimit = useCallback(async () => {
    try {
      const data = await getRateLimit();
      setRateLimit(data);
      setCountdown(Math.max(0, Math.floor(data.seconds_until_reset)));
      lastApiCountdown.current = data.seconds_until_reset;
      lastFetchTime.current = Date.now();
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch rate limit");
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Effect 1: Poll REST API every 2 seconds
  useEffect(() => {
    fetchRateLimit();
    const interval = setInterval(fetchRateLimit, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchRateLimit]);

  // Effect 2: Decrement countdown every second
  useEffect(() => {
    const tick = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 0) return 0;
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(tick);
  }, []);

  return { rateLimit, countdown, isLoading, error };
}
