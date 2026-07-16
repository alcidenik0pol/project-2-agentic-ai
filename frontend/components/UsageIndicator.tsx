"use client";

import { useEffect, useState } from "react";
import { Zap, Wrench } from "lucide-react";

interface UsageData {
  tracking_enabled: boolean;
  used: number;
  limit: number;
  percent_remaining: number;
  remaining: number;
}

export function UsageIndicator() {
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const fetchUsage = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8901";
        const res = await fetch(`${apiUrl}/api/v1/usage`);
        if (res.ok) {
          const data = await res.json();
          setUsage({
            tracking_enabled: data.tracking_enabled !== false, // backend omits/true in prod
            used: data.used,
            limit: data.limit,
            percent_remaining: data.percent_remaining,
            remaining: data.remaining,
          });
          setError(false);
        } else {
          setError(true);
        }
      } catch (e) {
        console.error("Failed to fetch usage:", e);
        setError(true);
      }
    };

    fetchUsage();
    // Refresh every 30 seconds
    const interval = setInterval(fetchUsage, 30000);
    return () => clearInterval(interval);
  }, []);

  if (error || !usage) {
    return null; // Don't show anything if we can't fetch usage
  }

  // Dev mode: token tracking disabled, show a small DEV badge.
  if (!usage.tracking_enabled) {
    return (
      <div
        className="flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-mono bg-amber-500/10"
        title="Local dev mode — token counting and monthly limits are disabled (APP_ENV=development)"
      >
        <Wrench className="w-3 h-3 text-amber-500" />
        <span className="text-amber-500">DEV</span>
      </div>
    );
  }

  const formatNumber = (n: number) => {
    if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
    if (n >= 1000) return `${(n / 1000).toFixed(0)}K`;
    return n.toString();
  };

  // Color based on remaining percentage
  const getColor = () => {
    if (usage.percent_remaining > 50) return "text-green-500";
    if (usage.percent_remaining > 20) return "text-amber-500";
    return "text-red-500";
  };

  const getBgColor = () => {
    if (usage.percent_remaining > 50) return "bg-green-500/10";
    if (usage.percent_remaining > 20) return "bg-amber-500/10";
    return "bg-red-500/10";
  };

  return (
    <div
      className={`flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-mono ${getBgColor()}`}
      title={`${formatNumber(usage.remaining)} tokens remaining (${usage.percent_remaining.toFixed(0)}%)`}
    >
      <Zap className={`w-3 h-3 ${getColor()}`} />
      <span className={getColor()}>
        {usage.percent_remaining.toFixed(0)}%
      </span>
    </div>
  );
}
