"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { ClusteringEDAResult } from "@/lib/types";

interface ClusteringEDATableProps {
  data: ClusteringEDAResult;
}

export function ClusteringEDATable({ data }: ClusteringEDATableProps) {
  const sortedClusters = [...data.cluster_details].sort(
    (a, b) => b.total_upvotes - a.total_upvotes
  );

  return (
    <div className="space-y-4">
      {/* Summary Stats */}
      <Card className="border-border">
        <CardHeader>
          <CardTitle className="text-lg">Clustering Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Original Themes</p>
              <p className="text-2xl font-bold">{data.summary.original_theme_count}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Final Clusters</p>
              <p className="text-2xl font-bold">{data.summary.final_cluster_count}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Dedup Ratio</p>
              <p className="text-2xl font-bold">{data.summary.deduplication_ratio}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Total Upvotes</p>
              <p className="text-2xl font-bold">
                {data.summary.total_upvotes_in_clusters.toLocaleString()}
              </p>
            </div>
          </div>
          <div className="mt-3 text-xs text-muted-foreground">
            Embedding: {data.summary.embedding_model} &middot; Provider: {data.summary.provider_used} &middot; Time: {data.summary.processing_time_seconds}s
          </div>
          {data.cluster_size_stats && (
            <div className="mt-1 text-xs text-muted-foreground">
              Cluster sizes &mdash; min: {data.cluster_size_stats.min}, max: {data.cluster_size_stats.max}, mean: {data.cluster_size_stats.mean}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Cluster Details Table */}
      <Card className="border-border">
        <CardHeader>
          <CardTitle className="text-lg">Cluster Details</CardTitle>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[400px]">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-background">
                <tr className="border-b border-border">
                  <th className="text-left p-2 w-10">#</th>
                  <th className="text-left p-2">Cluster Name</th>
                  <th className="text-right p-2 w-16">Posts</th>
                  <th className="text-right p-2 w-24">Upvotes</th>
                  <th className="text-right p-2 w-24">Avg Upvotes</th>
                </tr>
              </thead>
              <tbody>
                {sortedClusters.map((cluster) => (
                  <tr key={cluster.id} className="border-b border-border/50">
                    <td className="p-2 text-muted-foreground">{cluster.id}</td>
                    <td className="p-2">
                      <div>
                        <div className="font-medium">{cluster.name}</div>
                        <div className="text-xs text-muted-foreground">
                          {cluster.theme_count} themes
                        </div>
                      </div>
                    </td>
                    <td className="p-2 text-right">{cluster.post_count}</td>
                    <td className="p-2 text-right">
                      {cluster.total_upvotes.toLocaleString()}
                    </td>
                    <td className="p-2 text-right">
                      {cluster.avg_upvotes.toFixed(1)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </ScrollArea>
        </CardContent>
      </Card>

      {/* Theme Breakdown by Cluster */}
      <Card className="border-border">
        <CardHeader>
          <CardTitle className="text-lg">Theme Breakdown by Cluster</CardTitle>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[500px]">
            <div className="space-y-4">
              {sortedClusters.map((cluster) => (
                <div
                  key={cluster.id}
                  className="border border-border rounded-md p-4"
                >
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium">{cluster.name}</h4>
                    <Badge variant="secondary">
                      {cluster.post_count} posts &middot;{" "}
                      {cluster.total_upvotes.toLocaleString()} upvotes
                    </Badge>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {cluster.themes.map((theme, idx) => (
                      <Badge key={idx} variant="outline" className="text-xs">
                        {theme}
                      </Badge>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
}
