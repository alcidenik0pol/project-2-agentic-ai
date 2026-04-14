"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { BusinessIdea } from "@/lib/types";

const CONFIDENCE_STYLES: Record<string, string> = {
  high: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  medium: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  low: "bg-secondary/40 text-muted-foreground",
};

/** Split a comma-separated or newline-separated string into individual items. */
function splitList(text: string): string[] {
  return text
    .split(/[,\n]/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

export function IdeaCard({ idea }: { idea: BusinessIdea }) {
  const [expanded, setExpanded] = useState(false);
  const features = idea.core_features ? splitList(idea.core_features) : [];

  return (
    <Card className="border-border">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <span className="text-muted-foreground text-sm">#{idea.rank}</span>
            {idea.idea_name}
          </CardTitle>
          <Badge variant="outline" className={CONFIDENCE_STYLES[idea.confidence]}>
            {idea.confidence.toUpperCase()}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Pain Point */}
        <div>
          <span className="text-xs font-medium text-muted-foreground">Pain Point</span>
          <p className="text-sm mt-0.5">{idea.pain_point}</p>
        </div>

        {/* Solution */}
        <div>
          <span className="text-xs font-medium text-muted-foreground">Solution</span>
          <p className="text-sm mt-0.5">{idea.solution_description}</p>
        </div>

        {/* Core Features - prominent */}
        {features.length > 0 && (
          <div className="bg-secondary/50 rounded-md p-3 border border-secondary">
            <span className="text-xs font-semibold text-foreground">Core Features</span>
            <ul className="mt-1.5 space-y-1">
              {features.map((feature, i) => (
                <li key={i} className="text-sm flex items-start gap-1.5">
                  <span className="text-primary mt-1 flex-shrink-0">&bull;</span>
                  <span>{feature}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Revenue Model - prominent */}
        {idea.revenue_model && (
          <div className="bg-secondary/50 rounded-md p-3 border border-secondary">
            <span className="text-xs font-semibold text-foreground">Revenue Model</span>
            <p className="text-sm mt-0.5">{idea.revenue_model}</p>
          </div>
        )}

        {/* First User Step - prominent */}
        {idea.first_user_step && (
          <div className="bg-secondary/50 rounded-md p-3 border border-secondary">
            <span className="text-xs font-semibold text-foreground">First User Step</span>
            <p className="text-sm mt-0.5">{idea.first_user_step}</p>
          </div>
        )}

        {/* Target User */}
        <div>
          <span className="text-xs font-medium text-muted-foreground">Target User</span>
          <p className="text-sm mt-0.5">{idea.target_user}</p>
        </div>

        {/* Expandable evidence section */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-primary hover:underline"
        >
          {expanded ? "Hide" : "Show"} evidence
        </button>
        {expanded && (
          <div className="bg-secondary/50 rounded-md p-3 text-xs space-y-1">
            <div>Cluster: <strong>{idea.evidence.cluster_name}</strong></div>
            <div>Posts: {idea.evidence.post_count} | Upvotes: {idea.evidence.total_upvotes.toLocaleString()}</div>
            {idea.evidence.supporting_post_titles.length > 0 && (
              <div>
                <span className="text-muted-foreground">Supporting posts:</span>
                <ul className="list-disc pl-4 mt-1">
                  {idea.evidence.supporting_post_titles.map((title, i) => (
                    <li key={i}>{title}</li>
                  ))}
                </ul>
              </div>
            )}
            <div className="text-muted-foreground pt-1">{idea.confidence_reasoning}</div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
