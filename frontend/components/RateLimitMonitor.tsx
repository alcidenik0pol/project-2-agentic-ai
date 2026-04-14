"use client";

import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { useRateLimit } from "@/hooks/useRateLimit";

export function RateLimitMonitor() {
  const { rateLimit, countdown, isLoading, error } = useRateLimit();

  // Loading skeleton on first fetch
  if (isLoading) {
    return (
      <div className="space-y-2 w-[180px]">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Rate Limit
          </span>
          <Badge variant="secondary">...</Badge>
        </div>
        <div className="h-1.5 bg-secondary animate-pulse" />
        <div className="h-3 w-24 bg-secondary animate-pulse" />
      </div>
    );
  }

  // Error state
  if (error || !rateLimit) {
    return (
      <div className="space-y-2 w-[180px]">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Rate Limit
          </span>
          <Badge variant="secondary">Offline</Badge>
        </div>
        <Progress value={0} className="h-1.5" />
        <div className="text-[10px] text-muted-foreground">
          Backend unavailable
        </div>
      </div>
    );
  }

  const percentage = ((rateLimit.limit - rateLimit.requests_remaining) / rateLimit.limit) * 100;
  const resetMinutes = Math.floor(countdown / 60);
  const resetSeconds = countdown % 60;

  return (
    <div className="space-y-2 w-[180px]">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          Rate Limit
        </span>
        <Badge variant={rateLimit.is_throttled ? "destructive" : "secondary"}>
          {rateLimit.is_throttled ? "Throttled" : "OK"}
        </Badge>
      </div>
      <Progress value={percentage} className="h-1.5" />
      <div className="flex items-center justify-between text-[10px] text-muted-foreground">
        <span>
          {rateLimit.requests_remaining} / {rateLimit.limit} remaining
        </span>
        <span>
          Reset: {resetMinutes}:{resetSeconds.toString().padStart(2, "0")}
        </span>
      </div>
    </div>
  );
}
