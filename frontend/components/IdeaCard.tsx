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

/** Split a comma-separated or newline-separated string into individual items.
 *  Skips commas inside parentheses so "(Live, At Risk, Delisted)" stays intact. */
function splitList(text: string): string[] {
  return text
    .split(/,(?![^(]*\))/)
    .flatMap((part) => part.split(/\n/))
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
          <span className="text-xs font-medium text-muted-foreground">The Pain</span>
          <p className="text-sm mt-0.5">{idea.pain_point}</p>
        </div>

        {/* Solution */}
        <div>
          <span className="text-xs font-medium text-muted-foreground">The Pan</span>
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
          <div className="bg-secondary/50 rounded-md p-3 text-xs space-y-2">
            {/* Cluster header with themes */}
            <div>
              <div className="font-semibold text-foreground">
                Cluster: {idea.evidence.cluster_name}
              </div>
              {idea.evidence.cluster_themes.length > 0 && (
                <div className="text-muted-foreground mt-0.5">
                  Themes: {idea.evidence.cluster_themes.join(", ")}
                </div>
              )}
            </div>

            {/* Stats */}
            <div className="flex gap-3 text-muted-foreground">
              <span>{idea.evidence.post_count} posts in cluster</span>
              <span>{idea.evidence.total_upvotes.toLocaleString()} total upvotes</span>
            </div>

            {/* Supporting posts with links */}
            {idea.evidence.supporting_posts.length > 0 && (
              <div>
                <div className="text-xs font-medium text-foreground mb-1">
                  Top {idea.evidence.supporting_posts.length} posts by upvotes:
                </div>
                <ul className="space-y-1.5">
                  {idea.evidence.supporting_posts.map((post, i) => (
                    <li key={i} className="flex items-start gap-1.5">
                      <span className="text-primary mt-0.5 flex-shrink-0">&bull;</span>
                      <div className="flex-1 min-w-0">
                        <a
                          href={post.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="hover:text-primary hover:underline block"
                        >
                          {post.title}
                        </a>
                        <div className="text-muted-foreground text-[10px] mt-0.5">
                          {post.subreddit} &bull; {post.upvotes.toLocaleString()} upvotes
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Confidence reasoning */}
            <div className="text-muted-foreground pt-1 border-t border-secondary/70">
              {idea.confidence_reasoning}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
