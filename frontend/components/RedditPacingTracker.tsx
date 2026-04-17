"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { getRateLimit } from "@/lib/api";
import { useRequestQueue, type QueueItem } from "@/hooks/useRequestQueue";
import type { RateLimitStatus, AgentState } from "@/lib/types";

const POLL_INTERVAL_MS = 2000;
const PACING_INTERVAL_S = 6;

// ── Sub-components ──

const BURST_PARTICLES = [
  { tx: -12, ty: -20, delay: 0,  size: 7, color: "#34d399" },
  { tx: 14,  ty: -16, delay: 30, size: 5, color: "#6ee7b7" },
  { tx: -18, ty: -10, delay: 50, size: 4, color: "#22c55e" },
  { tx: 20,  ty: -6,  delay: 15, size: 6, color: "#34d399" },
  { tx: -10, ty: 10,  delay: 60, size: 5, color: "#6ee7b7" },
  { tx: 16,  ty: 14,  delay: 25, size: 4, color: "#22c55e" },
  { tx: -8,  ty: 20,  delay: 40, size: 6, color: "#34d399" },
  { tx: 10,  ty: 18,  delay: 55, size: 5, color: "#6ee7b7" },
  { tx: 0,   ty: -22, delay: 10, size: 4, color: "#22c55e" },
  { tx: 0,   ty: 22,  delay: 45, size: 5, color: "#34d399" },
  { tx: -20, ty: 0,   delay: 35, size: 3, color: "#6ee7b7" },
  { tx: 22,  ty: -2,  delay: 20, size: 3, color: "#22c55e" },
];

export function PacingTimer({ seconds }: { seconds: number }) {
  const [display, setDisplay] = useState(seconds);
  const [exploding, setExploding] = useState(false);
  const prevDisplayRef = useRef(seconds);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setDisplay(seconds);
  }, [seconds]);

  useEffect(() => {
    const timer = setInterval(() => {
      setDisplay((prev) => Math.max(0, prev - 0.1));
    }, 100);
    return () => clearInterval(timer);
  }, []);

  // Fire explosion on the transition from positive → zero (bar reaches full)
  useEffect(() => {
    if (prevDisplayRef.current > 0 && display <= 0) {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      setExploding(true);
      timeoutRef.current = setTimeout(() => setExploding(false), 700);
    }
    prevDisplayRef.current = display;
  }, [display]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  const pct = Math.min(100, ((PACING_INTERVAL_S - display) / PACING_INTERVAL_S) * 100);

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between h-7">
        <span className="text-[11px] text-muted-foreground uppercase tracking-wider">
          Next request in
        </span>
        <span
          className="text-sm font-mono font-medium bg-clip-text text-transparent"
          style={{ backgroundImage: "linear-gradient(to right, #34d399, #22c55e)" }}
        >
          {display.toFixed(1)}s
        </span>
      </div>

      <div className="relative h-2">
        <div className="h-full bg-secondary rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-100"
            style={{
              width: `${pct}%`,
              backgroundImage: "linear-gradient(to right, #34d399, #22c55e)",
            }}
          />
        </div>

        {/* Liquid explosion when bar fills */}
        {exploding && (
          <>
            <style>{`
              @keyframes liq-drop {
                0%   { transform: translate(0, 0) scale(1); opacity: 1; }
                50%  { opacity: 0.9; }
                100% { transform: translate(var(--tx), var(--ty)) scale(0); opacity: 0; }
              }
              @keyframes liq-ring {
                0%   { transform: scale(0.3); opacity: 0.7; }
                100% { transform: scale(3);   opacity: 0; }
              }
              @keyframes liq-flash {
                0%   { opacity: 0.5; filter: blur(4px); }
                100% { opacity: 0;   filter: blur(6px); }
              }
            `}</style>

            {/* Expanding glow ring */}
            <div
              className="absolute rounded-full pointer-events-none"
              style={{
                right: 0,
                top: "50%",
                width: 28,
                height: 28,
                transform: "translate(0, -50%)",
                background: "radial-gradient(circle, rgba(52,211,153,0.5) 0%, transparent 70%)",
                animation: "liq-ring 0.55s ease-out forwards",
              }}
            />

            {/* Burst particles */}
            {BURST_PARTICLES.map((p, i) => (
              <div
                key={i}
                className="absolute rounded-full pointer-events-none"
                style={{
                  right: 2,
                  top: "50%",
                  width: p.size,
                  height: p.size,
                  backgroundColor: p.color,
                  boxShadow: `0 0 4px ${p.color}80`,
                  "--tx": `${p.tx}px`,
                  "--ty": `${p.ty}px`,
                  transform: "translate(0, -50%)",
                  animation: `liq-drop 0.55s ease-out ${p.delay}ms forwards`,
                } as React.CSSProperties}
              />
            ))}

            {/* Bar glow flash */}
            <div
              className="absolute inset-0 rounded-full pointer-events-none"
              style={{
                backgroundImage: "linear-gradient(to right, #34d399, #22c55e)",
                animation: "liq-flash 0.4s ease-out forwards",
              }}
            />
          </>
        )}
      </div>
    </div>
  );
}

function PacingExplanation() {
  return (
    <div className="text-[11px] text-muted-foreground space-y-1 border-t border-border pt-3">
      <p className="font-medium text-foreground text-[12px]">How rate limiting works</p>
      <p>Reddit API: 100 requests per 10 minutes</p>
      <ul className="list-disc list-inside space-y-0.5 pl-1">
        <li>1 request every 6 seconds (600s / 100 = 6s)</li>
        <li>No bursting &mdash; prevents WAF blocking</li>
        <li>Routed through SOCKS5 proxy for residential IP routing</li>
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
      <div className="flex items-center justify-between h-7">
        <span className="text-[11px] text-muted-foreground uppercase tracking-wider">
          Request queue
        </span>
        <span className="text-sm font-mono font-medium text-foreground">
          {requestsInWindow}
          <span className="text-muted-foreground">/{limit}</span>{" "}
          <span className="text-muted-foreground">used</span>
        </span>
      </div>

      {/* Window budget bar */}
      <div className="h-2 bg-secondary rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${Math.min(100, (requestsInWindow / limit) * 100)}%`,
            backgroundImage: "linear-gradient(to right, #34d399, #22c55e)",
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
                    backgroundColor:
                      item.status === "sent"
                        ? "#34d399"
                        : item.status === "error"
                        ? "#f87171"
                        : "#6ee7b7",
                  }}
                />
                <span className="text-[12px] flex-1 truncate">{item.name}</span>
                <span className="text-[11px] text-muted-foreground">{item.elapsed}s</span>
                <span
                  className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                    item.status === "sent"
                      ? "bg-emerald-500/10 text-emerald-400"
                      : item.status === "error"
                      ? "bg-red-500/10 text-red-400"
                      : "bg-emerald-500/10 text-emerald-300"
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
        <div className="bg-emerald-500/10 rounded-md p-2 text-[12px] text-emerald-400">
          Approaching limit. New requests are being queued.
        </div>
      )}
      {requestsInWindow >= limit && (
        <div className="bg-red-500/10 rounded-md p-2 text-[12px] text-red-400">
          Limit reached. Queued requests will fire when the window resets.
        </div>
      )}
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
    </div>
  );
}
