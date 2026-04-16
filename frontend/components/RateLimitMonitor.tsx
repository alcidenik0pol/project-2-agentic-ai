"use client";

import { useRateLimit } from "@/hooks/useRateLimit";
import { useRequestQueue, type QueueItem } from "@/hooks/useRequestQueue";
import type { AgentState } from "@/lib/types";

function barColor(pct: number): string {
  if (pct < 60) return "#639922";
  if (pct < 85) return "#BA7517";
  return "#A32D2D";
}

function Pill({ status }: { status: QueueItem["status"] }) {
  const styles: Record<QueueItem["status"], string> = {
    sent: "bg-[#EAF3DE] text-[#3B6D11]",
    waiting: "bg-[#FAEEDA] text-[#854F0B]",
    error: "bg-[#FCEBEB] text-[#791F1F]",
  };
  return (
    <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${styles[status]}`}>
      {status}
    </span>
  );
}

interface RateLimitMonitorProps {
  agents?: AgentState[];
}

export function RateLimitMonitor({ agents }: RateLimitMonitorProps) {
  const { rateLimit, countdown, isLoading, error } = useRateLimit();
  const queue = useRequestQueue(agents ?? []);

  // Loading skeleton
  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="grid grid-cols-3 gap-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-secondary/50 rounded-md p-3 h-[72px]" />
          ))}
        </div>
        <div className="h-2 bg-secondary rounded-full" />
      </div>
    );
  }

  // Error state
  if (error || !rateLimit) {
    return (
      <div className="text-center text-muted-foreground text-sm py-6">
        Backend unavailable
      </div>
    );
  }

  const used = rateLimit.limit - rateLimit.requests_remaining;
  const pct = Math.round((used / rateLimit.limit) * 100);
  const mm = Math.floor(countdown / 60);
  const ss = String(countdown % 60).padStart(2, "0");

  return (
    <div className="space-y-4">
      {/* Metric cards */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-secondary/50 rounded-md p-3">
          <div className="text-[11px] text-muted-foreground uppercase tracking-wider mb-1">Used</div>
          <div className="text-2xl font-medium leading-none">
            {used}<span className="text-sm text-muted-foreground ml-0.5">/ {rateLimit.limit}</span>
          </div>
        </div>
        <div className="bg-secondary/50 rounded-md p-3">
          <div className="text-[11px] text-muted-foreground uppercase tracking-wider mb-1">Remaining</div>
          <div className="text-2xl font-medium leading-none">{rateLimit.requests_remaining}</div>
        </div>
        <div className="bg-secondary/50 rounded-md p-3">
          <div className="text-[11px] text-muted-foreground uppercase tracking-wider mb-1">Resets in</div>
          <div className="text-2xl font-medium leading-none">
            {mm}:{ss}<span className="text-sm text-muted-foreground ml-0.5">min</span>
          </div>
        </div>
      </div>

      {/* Budget bar */}
      <div>
        <div className="text-[11px] text-muted-foreground uppercase tracking-wider mb-2">Request budget</div>
        <div className="h-2 bg-secondary rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${pct}%`, background: barColor(pct) }}
          />
        </div>
        <div className="flex justify-between text-[11px] text-muted-foreground mt-1">
          <span>0</span>
          <span>{pct}% used</span>
          <span>{rateLimit.limit}</span>
        </div>
      </div>

      {/* Warning banner */}
      {pct >= 80 && pct < 100 && (
        <div className="bg-[#FAEEDA] rounded-md p-2.5 text-[13px] text-[#633806]">
          Approaching limit. New requests are being queued.
        </div>
      )}
      {pct >= 100 && (
        <div className="bg-[#FCEBEB] rounded-md p-2.5 text-[13px] text-[#791F1F]">
          Limit reached. Queued requests will fire when the window resets.
        </div>
      )}

      {/* Live queue */}
      <div>
        <div className="text-[13px] font-medium text-muted-foreground mt-1 mb-2">Live queue</div>
        {queue.length === 0 ? (
          <div className="text-[13px] text-muted-foreground py-2">No pending requests.</div>
        ) : (
          <div className="divide-y divide-border">
            {queue.map((item) => (
              <div key={item.id} className="flex items-center gap-2.5 py-2.5">
                <div
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{
                    background:
                      item.status === "sent" ? "#639922" :
                      item.status === "error" ? "#A32D2D" : "#BA7517",
                  }}
                />
                <span className="text-[13px]">{item.name}</span>
                <span className="text-[12px] text-muted-foreground">{item.elapsed}s ago</span>
                <Pill status={item.status} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
