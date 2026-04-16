"use client";

import { RedditPacingTracker } from "@/components/RedditPacingTracker";
import Link from "next/link";

export default function RateLimitPage() {
  return (
    <div className="flex flex-col items-center px-4 py-8">
      <div className="w-full max-w-2xl">
        <h1 className="text-lg font-bold mb-1">Reddit API Rate Limit</h1>
        <p className="text-xs text-muted-foreground mb-6">
          Reddit enforces 100 requests per 10 minutes. Requests are paced at 1 every 6 seconds
          to stay within limits and avoid WAF blocking.
        </p>

        <div className="border border-white/10 rounded-lg bg-card p-[12px_16px]">
          <RedditPacingTracker />
        </div>

        <div className="mt-6 border border-white/10 rounded-lg bg-card p-4 space-y-3">
          <h2 className="text-sm font-medium">How rate limiting works</h2>
          <ul className="text-xs text-muted-foreground space-y-2 list-disc list-inside">
            <li>Reddit allows 100 requests per 10 minutes per IP for unauthenticated access.</li>
            <li>We pace requests evenly: 1 request every 6 seconds (600s / 100 = 6s).</li>
            <li>No bursting &mdash; this prevents Reddit&apos;s WAF from blocking data center IPs.</li>
            <li>The 6-second timer above counts down to the next available request slot.</li>
          </ul>
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
