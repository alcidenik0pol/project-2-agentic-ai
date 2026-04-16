"use client";

import { useState, useEffect, useCallback } from "react";
import { getRateLimit } from "@/lib/api";
import { useRequestQueue, type QueueItem } from "@/hooks/useRequestQueue";
import type { RateLimitStatus, AgentState } from "@/lib/types";

const POLL_INTERVAL_MS = 2000;
const PACING_INTERVAL_S = 6;

// ── Sub-components ──

function PacingTimer({ seconds }: { seconds: number }) {
  const [display, setDisplay] = useState(seconds);

  // Smooth local countdown (100ms ticks)
  useEffect(() => {
    setDisplay(seconds);
  }, [seconds]);

  useEffect(() => {
    const timer = setInterval(() => {
      setDisplay((prev) => Math.max(0, prev - 0.1));
    }, 100);
    return () => clearInterval(timer);
  }, []);

  const pct = Math.min(100, ((PACING_INTERVAL_S - display) / PACING_INTERVAL_S) * 100);
  const color = display > 3 ? "#639922" : display > 1 ? "#BA7517" : "#A32D2D";

  return (
    <div className="space-y-2">
      <div className="flex items-baseline justify-between">
        <span className="text-[11px] text-muted-foreground uppercase tracking-wider">
          Next request in
        </span>
        <span className="text-2xl font-mono font-medium" style={{ color }}>
          {display.toFixed(1)}s
        </span>
      </div>
      <div className="h-2 bg-secondary rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-100"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  );
}

function PacingExplanation() {
  return (
    <div className="text-[11px] text-muted-foreground space-y-1 border-t border-border pt-3">
      <p className="font-medium text-foreground text-[12px]">How pacing works</p>
      <p>Reddit API: 100 requests per 10 minutes</p>
      <ul className="list-disc list-inside space-y-0.5 pl-1">
        <li>1 request every 6 seconds (600s / 100 = 6s)</li>
        <li>No bursting &mdash; prevents WAF blocking</li>
        <li>Proxy-enabled for residential IP routing</li>
      </ul>
    </div>
  );
}

function QueueInformation({
  queue,
  requestsRemaining,
  requestsInWindow,
  limit,
}: {
  queue: QueueItem[];
  requestsRemaining: number;
  requestsInWindow: number;
  limit: number;
}) {
  const completed = queue.filter((q) => q.status === "sent").length;
  const total = queue.length;

  return (
    <div className="space-y-2 border-t border-border pt-3">
      <div className="flex items-center justify-between">
        <span className="text-[11px] text-muted-foreground uppercase tracking-wider">
          Request queue
        </span>
        <span className="text-[12px] font-mono">
          {requestsInWindow}
          <span className="text-muted-foreground">/{limit}</span>{" "}
          <span className="text-muted-foreground">used</span>
        </span>
      </div>

      {/* Window budget bar */}
      <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${Math.min(100, (requestsInWindow / limit) * 100)}%`,
            background:
              requestsInWindow / limit < 0.6
                ? "#639922"
                : requestsInWindow / limit < 0.85
                ? "#BA7517"
                : "#A32D2D",
          }}
        />
      </div>

      {/* Queue items */}
      {total === 0 ? (
        <p className="text-[12px] text-muted-foreground py-1">No pending requests.</p>
      ) : (
        <div className="space-y-1.5">
          <p className="text-[11px] text-muted-foreground">
            {completed}/{total} completed
          </p>
          <div className="divide-y divide-border">
            {queue.map((item) => (
              <div key={item.id} className="flex items-center gap-2 py-1.5">
                <div
                  className="w-1.5 h-1.5 rounded-full shrink-0"
                  style={{
                    background:
                      item.status === "sent"
                        ? "#639922"
                        : item.status === "error"
                        ? "#A32D2D"
                        : "#BA7517",
                  }}
                />
                <span className="text-[12px] flex-1 truncate">{item.name}</span>
                <span className="text-[11px] text-muted-foreground">{item.elapsed}s</span>
                <span
                  className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                    item.status === "sent"
                      ? "bg-[#EAF3DE] text-[#3B6D11]"
                      : item.status === "error"
                      ? "bg-[#FCEBEB] text-[#791F1F]"
                      : "bg-[#FAEEDA] text-[#854F0B]"
                  }`}
                >
                  {item.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Budget warnings */}
      {requestsInWindow / limit >= 0.8 && requestsInWindow / limit < 1 && (
        <div className="bg-[#FAEEDA] rounded-md p-2 text-[12px] text-[#633806]">
          Approaching limit. New requests are being queued.
        </div>
      )}
      {requestsInWindow >= limit && (
        <div className="bg-[#FCEBEB] rounded-md p-2 text-[12px] text-[#791F1F]">
          Limit reached. Queued requests will fire when the window resets.
        </div>
      )}
    </div>
  );
}

function ProxyReference() {
  return (
    <div className="border-t border-border pt-3 text-[11px] text-muted-foreground">
      <p>
        Requests routed through SOCKS5 proxy to bypass Reddit WAF blocks on data center IPs.
      </p>
      <p className="mt-0.5">
        See{" "}
        <code className="text-[10px] bg-secondary px-1 py-0.5 rounded">
          docs/traces/2026-04-16_socks5-proxy-reddit-waf-fix.md
        </code>{" "}
        for details.
      </p>
    </div>
  );
}

// ── Main hook ──

function usePacingRateLimit() {
  const [rateLimit, setRateLimit] = useState<RateLimitStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRateLimit = useCallback(async () => {
    try {
      const data = await getRateLimit();
      setRateLimit(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch rate limit");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRateLimit();
    const interval = setInterval(fetchRateLimit, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchRateLimit]);

  return { rateLimit, isLoading, error };
}

// ── Main component ──

interface RedditPacingTrackerProps {
  agents?: AgentState[];
}

export function RedditPacingTracker({ agents }: RedditPacingTrackerProps) {
  const { rateLimit, isLoading, error } = usePacingRateLimit();
  const queue = useRequestQueue(agents ?? []);

  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 bg-secondary/50 rounded-md" />
        <div className="h-2 bg-secondary rounded-full" />
        <div className="h-16 bg-secondary/50 rounded-md" />
      </div>
    );
  }

  if (error || !rateLimit) {
    return (
      <div className="text-center text-muted-foreground text-sm py-6">
        Backend unavailable
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <PacingTimer seconds={rateLimit.seconds_until_next_request} />
      <QueueInformation
        queue={queue}
        requestsRemaining={rateLimit.requests_remaining}
        requestsInWindow={rateLimit.requests_in_window}
        limit={rateLimit.limit}
      />
      <PacingExplanation />
      <ProxyReference />
    </div>
  );
}
