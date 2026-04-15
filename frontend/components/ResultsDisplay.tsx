"use client";

import { Card, CardContent } from "@/components/ui/card";
import type { HypothesisOutput } from "@/lib/types";
import { IdeaCard } from "@/components/IdeaCard";

interface ResultsDisplayProps {
  hypothesis: HypothesisOutput | null;
  reportContent: string | null;
}

export function ResultsDisplay({ hypothesis, reportContent }: ResultsDisplayProps) {
  if (!hypothesis) {
    return (
      <Card className="border-border">
        <CardContent className="p-8 text-center text-muted-foreground">
          Results will appear here after analysis completes.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {hypothesis.analysis_summary && (
        <p className="text-sm text-muted-foreground">{hypothesis.analysis_summary}</p>
      )}
      {hypothesis.ideas.map((idea) => (
        <IdeaCard key={idea.rank} idea={idea} />
      ))}
      {hypothesis.data_limitations && (
        <div className="text-xs text-muted-foreground mt-4 p-3 bg-secondary/30 rounded-md">
          <strong>Data Limitations:</strong> {hypothesis.data_limitations}
        </div>
      )}
    </div>
  );
}
