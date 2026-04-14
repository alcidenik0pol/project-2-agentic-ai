"use client";

import { RateLimitMonitor } from "@/components/RateLimitMonitor";
import Link from "next/link";

export default function RateLimitPage() {
  return (
    <div className="flex flex-col items-center px-4 py-8">
      <div className="w-full max-w-2xl">
        <h1 className="text-lg font-bold mb-1">Reddit API Rate Limit</h1>
        <p className="text-xs text-muted-foreground mb-6">
          Monitor the current Reddit API rate limit status. The backend polls Reddit&apos;s
          rate limit headers on every request and exposes the current quota here.
        </p>

        <div className="border border-border p-6 bg-card">
          <RateLimitMonitor />
        </div>

        <div className="mt-6 border border-border p-4 bg-card space-y-3">
          <h2 className="text-sm font-medium">How rate limiting works</h2>
          <ul className="text-xs text-muted-foreground space-y-2 list-disc list-inside">
            <li>Reddit enforces a per-client request quota (typically 100 requests per minute).</li>
            <li>Each Reddit API call made during analysis consumes one request from the quota.</li>
            <li>When the quota is exhausted, requests are throttled until the window resets.</li>
            <li>The reset countdown shows time until the quota refreshes.</li>
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
