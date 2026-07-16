"use client";

import { RedditPacingTracker } from "@/components/RedditPacingTracker";
import { useGlobalWebSocket } from "@/hooks/useGlobalWebSocket";
import Link from "next/link";

export default function RateLimitPage() {
  const { agents } = useGlobalWebSocket();
  return (
    <div className="flex flex-col items-center px-4 py-8">
      <div className="w-full max-w-2xl">
        <h1 className="text-lg font-bold mb-1">Reddit API Rate Limit</h1>
        <p className="text-xs text-muted-foreground mb-6">
          Reddit enforces 100 requests per 10 minutes. Requests are paced at 1 every 6 seconds
          to stay within limits and avoid WAF blocking.
        </p>

        <div className="border border-white/10 rounded-lg bg-card p-[12px_16px]">
          <RedditPacingTracker agents={agents} />
        </div>

        <div className="mt-4">
          <Link
            href="/"
            className="text-xs text-muted-foreground hover:text-foreground transition-colors underline"
          >
            Back to Home
          </Link>
        </div>
      </div>
    </div>
  );
}
