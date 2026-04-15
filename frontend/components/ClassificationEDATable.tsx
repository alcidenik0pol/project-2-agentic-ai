"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { ClassificationEDAResult } from "@/lib/types";

interface ClassificationEDATableProps {
  data: ClassificationEDAResult;
}

export function ClassificationEDATable({ data }: ClassificationEDATableProps) {
  return (
    <div className="space-y-4">
      {/* Summary Stats */}
      <Card className="border-border">
        <CardHeader>
          <CardTitle className="text-lg">Classification Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Total Posts</p>
              <p className="text-2xl font-bold">{data.summary.total_posts}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Success Rate</p>
              <p className="text-2xl font-bold">{data.summary.success_rate}%</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Unique Themes</p>
              <p className="text-2xl font-bold">{data.unique_themes}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Processing Time</p>
              <p className="text-2xl font-bold">{data.summary.processing_time_seconds}s</p>
            </div>
          </div>
          <div className="mt-3 text-xs text-muted-foreground">
            Model: {data.summary.model_used} &middot; Throughput: {data.summary.posts_per_second} posts/s
          </div>
        </CardContent>
      </Card>

      {/* Complaint vs Non-Complaint */}
      <Card className="border-border">
        <CardHeader>
          <CardTitle className="text-lg">Complaint Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <div className="text-center p-4 bg-secondary/30 rounded-md">
              <p className="text-sm text-muted-foreground">Complaints</p>
              <p className="text-xl font-bold text-red-400">
                {data.complaint_vs_noncomplaint.complaint}
              </p>
            </div>
            <div className="text-center p-4 bg-secondary/30 rounded-md">
              <p className="text-sm text-muted-foreground">Non-Complaints</p>
              <p className="text-xl font-bold text-green-400">
                {data.complaint_vs_noncomplaint.non_complaint}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Intensity Distribution */}
      <Card className="border-border">
        <CardHeader>
          <CardTitle className="text-lg">Intensity Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {(["high", "medium", "low"] as const).map((level) => (
              <div key={level} className="flex items-center justify-between">
                <span className="capitalize">{level}</span>
                <Badge
                  variant={
                    level === "high"
                      ? "destructive"
                      : level === "medium"
                        ? "default"
                        : "secondary"
                  }
                >
                  {data.intensity_distribution[level]}
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Top Themes Table */}
      <Card className="border-border">
        <CardHeader>
          <CardTitle className="text-lg">Top 20 Themes</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left p-2 w-10">#</th>
                  <th className="text-left p-2">Theme</th>
                  <th className="text-right p-2 w-20">Count</th>
                </tr>
              </thead>
              <tbody>
                {data.top_20_themes.map((item, index) => (
                  <tr key={index} className="border-b border-border/50">
                    <td className="p-2 text-muted-foreground">{index + 1}</td>
                    <td className="p-2">{item.theme}</td>
                    <td className="p-2 text-right font-medium">{item.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
