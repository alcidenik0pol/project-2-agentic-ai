"use client";

import { useEffect, useRef, useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Check } from "lucide-react";
import { IdeaCard } from "@/components/IdeaCard";
import { ClassificationEDATable } from "@/components/ClassificationEDATable";
import { ClusteringEDATable } from "@/components/ClusteringEDATable";
import type {
  HypothesisOutput,
  ClassificationEDAResult,
  ClusteringEDAResult,
} from "@/lib/types";

interface TabbedResultsDisplayProps {
  hypothesis: HypothesisOutput | null;
  classificationEDA: ClassificationEDAResult | null;
  clusteringEDA: ClusteringEDAResult | null;
  query?: string;
  generationComplete?: boolean;
}

// ── Empty-state helpers for the Business Ideas tab ──
// When hypothesis generation fails, build a contextual explanation from
// the EDA/clustering data we already have instead of a generic string.

function StatBox({ label, value }: { label: string; value: number }) {
  return (
    <div className="text-center p-4 bg-secondary/30 rounded-md">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="text-xl font-bold">{value.toLocaleString()}</p>
    </div>
  );
}

function IdeasEmptyState({
  classificationEDA,
  clusteringEDA,
  query,
}: {
  classificationEDA: ClassificationEDAResult | null;
  clusteringEDA: ClusteringEDAResult | null;
  query?: string;
}) {
  const totalPosts = classificationEDA?.summary?.total_posts;
  const complaintCount = classificationEDA?.complaint_vs_noncomplaint?.complaint;
  const clusterCount = clusteringEDA?.summary?.final_cluster_count;
  const totalUpvotes = clusteringEDA?.summary?.total_upvotes_in_clusters;

  const hasComplaints = complaintCount !== undefined && complaintCount > 0;
  // Small-count qualifier so low signal reads as low signal ("only 3 complaints").
  const onlyPrefix =
    complaintCount !== undefined && complaintCount > 0 && complaintCount <= 5
      ? "only "
      : "";

  // Scenario-specific explanation: A1/A2 (both EDA), B1/B2 (classification only),
  // and a defensive fallback for the normally-unreachable "no EDA at all" case.
  let explanation: string;
  if (classificationEDA && clusteringEDA) {
    explanation = hasComplaints
      ? `Analyzed ${totalPosts} posts, identified ${onlyPrefix}${complaintCount} complaints across ${clusterCount} clusters. The final synthesis step failed to produce business ideas.`
      : `Processed ${totalPosts} posts, found 0 complaints — nothing to synthesize into business ideas.`;
  } else if (classificationEDA) {
    explanation = hasComplaints
      ? `Found ${onlyPrefix}${complaintCount} complaints in ${totalPosts} posts, but the clustering step failed.`
      : `Processed ${totalPosts} posts, found 0 complaints. Clustering had nothing to group.`;
  } else {
    explanation = "No business ideas were generated.";
  }

  // Collect stats conditionally so a missing field is omitted, never "undefined".
  const stats: Array<{ label: string; value: number }> = [];
  if (totalPosts !== undefined) stats.push({ label: "Posts Analyzed", value: totalPosts });
  if (complaintCount !== undefined) stats.push({ label: "Complaints Found", value: complaintCount });
  if (clusterCount !== undefined) stats.push({ label: "Clusters Formed", value: clusterCount });
  if (totalUpvotes !== undefined) stats.push({ label: "Total Upvotes", value: totalUpvotes });

  // Top 3 teasers: prefer cluster names (by upvotes), fall back to classification themes.
  let teasers: string[] = [];
  if (hasComplaints) {
    if (clusteringEDA) {
      teasers = [...clusteringEDA.cluster_details]
        .sort((a, b) => b.total_upvotes - a.total_upvotes)
        .slice(0, 3)
        .map((c) => c.name);
    } else if (classificationEDA) {
      teasers = classificationEDA.top_20_themes.slice(0, 3).map((t) => t.theme);
    }
  }

  return (
    <Card className="border-border">
      <CardContent className="p-6 space-y-4">
        <p className="text-sm text-muted-foreground">
          {query && (
            <span className="font-medium text-foreground">
              No business ideas for "{query}".{" "}
            </span>
          )}
          {explanation} Try a different query to surface actionable pain points.
        </p>

        {stats.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {stats.map((s) => (
              <StatBox key={s.label} label={s.label} value={s.value} />
            ))}
          </div>
        )}

        {teasers.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs text-muted-foreground">
              {clusteringEDA ? "Top clusters by upvotes" : "Top themes"}
            </p>
            <div className="flex flex-wrap gap-1.5">
              {teasers.map((label, idx) => (
                <Badge key={idx} variant="outline" className="text-xs">
                  {label}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function TabbedResultsDisplay({
  hypothesis,
  classificationEDA,
  clusteringEDA,
  query,
  generationComplete,
}: TabbedResultsDisplayProps) {
  const [activeTab, setActiveTab] = useState<string>(() => {
    // Pick the most-complete available tab at mount time so we never
    // land on a disabled tab in an edge-case mount order.
    if (hypothesis) return "ideas";
    if (clusteringEDA) return "clustering";
    if (classificationEDA) return "classification";
    return "classification";
  });

  // One-shot guards so each auto-switch fires exactly once per run,
  // then the user is free to click around without being yanked back.
  const switchedToClassification = useRef(false);
  const switchedToClustering = useRef(false);
  const switchedToIdeas = useRef(false);

  // Auto-switch to a tab the moment its data arrives.
  useEffect(() => {
    if (classificationEDA && !switchedToClassification.current) {
      switchedToClassification.current = true;
      setActiveTab("classification");
    }
  }, [classificationEDA]);

  useEffect(() => {
    if (clusteringEDA && !switchedToClustering.current) {
      switchedToClustering.current = true;
      setActiveTab("clustering");
    }
  }, [clusteringEDA]);

  useEffect(() => {
    // Switch to "Business Ideas" when the run finishes — either with results
    // (hypothesis arrived via WS) or empty (generationComplete with no
    // hypothesis → "No cases cracked"). Confetti in page.tsx is gated
    // on `hypothesis`, so it only fires on the success path.
    if ((hypothesis || generationComplete) && !switchedToIdeas.current) {
      switchedToIdeas.current = true;
      setActiveTab("ideas");
    }
  }, [hypothesis, generationComplete]);

  // Reset guards on new run, when all data clears.
  useEffect(() => {
    if (!classificationEDA && !clusteringEDA && !hypothesis) {
      switchedToClassification.current = false;
      switchedToClustering.current = false;
      switchedToIdeas.current = false;
      setActiveTab("classification");
    }
  }, [classificationEDA, clusteringEDA, hypothesis]);

  if (!hypothesis && !classificationEDA && !clusteringEDA) {
    return null;
  }

  return (
    <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
      {/* Vertical on mobile, horizontal on desktop */}
      <div className="flex flex-col sm:block">
        <TabsList className="flex flex-col sm:grid sm:grid-cols-3 w-full h-auto sm:h-10 gap-1">
          <TabsTrigger value="classification" disabled={!classificationEDA}>
            Classification EDA
            {classificationEDA && <Check className="w-4 h-4 ml-2 text-green-500" strokeWidth={3} />}
          </TabsTrigger>
          <TabsTrigger value="clustering" disabled={!clusteringEDA}>
            Clustering Results
            {clusteringEDA && <Check className="w-4 h-4 ml-2 text-green-500" strokeWidth={3} />}
          </TabsTrigger>
          <TabsTrigger value="ideas">
            Business Ideas
            {hypothesis && <Check className="w-4 h-4 ml-2 text-green-500" strokeWidth={3} />}
          </TabsTrigger>
        </TabsList>
      </div>

      <TabsContent value="classification" className="mt-4">
        {classificationEDA ? (
          <ClassificationEDATable data={classificationEDA} />
        ) : (
          <Card className="border-border">
            <CardContent className="p-8 text-center text-muted-foreground">
              Classification EDA appears once analysis completes.
            </CardContent>
          </Card>
        )}
      </TabsContent>

      <TabsContent value="clustering" className="mt-4">
        {clusteringEDA ? (
          <ClusteringEDATable data={clusteringEDA} />
        ) : (
          <Card className="border-border">
            <CardContent className="p-8 text-center text-muted-foreground">
              Clustering results appear once analysis completes.
            </CardContent>
          </Card>
        )}
      </TabsContent>

      <TabsContent value="ideas" className="space-y-4 mt-4">
        {hypothesis ? (
          <>
            {hypothesis.analysis_summary && (
              <div className="text-sm text-muted-foreground">
                {query && (
                  <span className="font-medium text-foreground">
                    Top complaint themes found for "{query}":
                  </span>
                )}
                <p className="mt-1">{hypothesis.analysis_summary}</p>
              </div>
            )}
            {hypothesis.ideas.map((idea) => (
              <IdeaCard key={idea.rank} idea={idea} />
            ))}
            {hypothesis.data_limitations && (
              <div className="text-xs text-muted-foreground mt-4 p-3 bg-secondary/30 rounded-md">
                <strong>Data Limitations:</strong> {hypothesis.data_limitations}
              </div>
            )}
          </>
        ) : generationComplete ? (
          <IdeasEmptyState
            classificationEDA={classificationEDA}
            clusteringEDA={clusteringEDA}
            query={query}
          />
        ) : (
          <Card className="border-border">
            <CardContent className="p-8 text-center text-muted-foreground">
              Generating report<span className="inline-flex animate-pulse">...</span>
            </CardContent>
          </Card>
        )}
      </TabsContent>
    </Tabs>
  );
}
