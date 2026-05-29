"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, Clock, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface UsageInfo {
  used: number;
  limit: number;
  resets_at: string;
}

export default function LimitExceededPage() {
  const [usageInfo, setUsageInfo] = useState<UsageInfo | null>(null);
  const [countdown, setCountdown] = useState<string>("");

  useEffect(() => {
    // Fetch current usage info
    const fetchUsage = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8901";
        const res = await fetch(`${apiUrl}/api/v1/usage`);
        if (res.ok) {
          const data = await res.json();
          setUsageInfo({
            used: data.used,
            limit: data.limit,
            resets_at: data.resets_at,
          });
        }
      } catch (e) {
        console.error("Failed to fetch usage info:", e);
      }
    };

    fetchUsage();
  }, []);

  // Update countdown timer
  useEffect(() => {
    if (!usageInfo?.resets_at) return;

    const updateCountdown = () => {
      const now = new Date();
      const reset = new Date(usageInfo.resets_at);
      const diff = reset.getTime() - now.getTime();

      if (diff <= 0) {
        setCountdown("Resetting soon...");
        return;
      }

      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

      if (days > 0) {
        setCountdown(`${days}d ${hours}h ${minutes}m`);
      } else if (hours > 0) {
        setCountdown(`${hours}h ${minutes}m`);
      } else {
        setCountdown(`${minutes}m`);
      }
    };

    updateCountdown();
    const interval = setInterval(updateCountdown, 60000); // Update every minute

    return () => clearInterval(interval);
  }, [usageInfo?.resets_at]);

  const formatNumber = (n: number) => {
    if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
    if (n >= 1000) return `${(n / 1000).toFixed(0)}K`;
    return n.toString();
  };

  const formatDate = (isoString: string) => {
    const date = new Date(isoString);
    return date.toLocaleDateString("en-US", {
      month: "long",
      day: "numeric",
      year: "numeric",
    });
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[80vh] px-4 py-8">
      <div className="w-full max-w-md text-center space-y-6">
        {/* Warning Icon */}
        <div className="mx-auto w-16 h-16 rounded-full bg-amber-500/10 flex items-center justify-center">
          <AlertTriangle className="w-8 h-8 text-amber-500" />
        </div>

        {/* Title */}
        <div>
          <h1 className="text-xl font-bold mb-2">Usage Limit Reached</h1>
          <p className="text-sm text-muted-foreground">
            This month's AI token budget has been exhausted.
          </p>
        </div>

        {/* Usage Stats */}
        {usageInfo && (
          <div className="border border-border rounded-lg bg-card p-4 space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Tokens Used</span>
              <span className="font-mono font-medium">
                {formatNumber(usageInfo.used)} / {formatNumber(usageInfo.limit)}
              </span>
            </div>

            {/* Progress Bar */}
            <div className="w-full h-2 bg-secondary rounded-full overflow-hidden">
              <div
                className="h-full bg-amber-500 transition-all"
                style={{ width: `${Math.min(100, (usageInfo.used / usageInfo.limit) * 100)}%` }}
              />
            </div>

            <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
              <Clock className="w-4 h-4" />
              <span>
                Resets on <span className="text-foreground">{formatDate(usageInfo.resets_at)}</span>
              </span>
            </div>

            {countdown && (
              <div className="text-xs text-muted-foreground font-mono">
                Time remaining: {countdown}
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-col gap-3">
          <Button
            variant="outline"
            onClick={() => window.location.reload()}
            className="w-full"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Check Again
          </Button>

          <Link href="/" className="w-full">
            <Button variant="ghost" className="w-full">
              Back to Home
            </Button>
          </Link>
        </div>

        {/* Info */}
        <p className="text-xs text-muted-foreground">
          The usage limit helps manage API costs. It automatically resets on the 1st of each month.
        </p>
      </div>
    </div>
  );
}
