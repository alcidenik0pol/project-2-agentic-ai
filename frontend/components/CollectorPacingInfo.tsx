import { PacingTimer } from "@/components/RedditPacingTracker";
import { RequestBudget } from "@/components/RequestBudget";
import type { RateLimitStatus, AgentProgress } from "@/lib/types";

interface CollectorPacingInfoProps {
  rateLimit: RateLimitStatus | null;
  agentProgress: AgentProgress | null;
}

export function CollectorPacingInfo({ rateLimit, agentProgress }: CollectorPacingInfoProps) {
  const remaining = agentProgress
    ? agentProgress.progress.total - agentProgress.progress.current
    : null;

  return (
    <div className="flex gap-4 items-stretch">
      <div className="flex-1 min-w-0">
        <PacingTimer seconds={rateLimit?.seconds_until_next_request ?? 0} />
      </div>
      <div className="flex-1 min-w-0">
        <RequestBudget
          requestsInWindow={rateLimit?.requests_in_window ?? 0}
          limit={rateLimit?.limit ?? 100}
        />
      </div>
      {remaining !== null && (
        <div className="flex flex-col justify-center min-w-[60px]">
          <span className="text-[11px] text-muted-foreground uppercase tracking-wider">
            Remaining
          </span>
          <span className="text-lg font-mono font-medium text-foreground">
            {remaining}
          </span>
        </div>
      )}
    </div>
  );
}
