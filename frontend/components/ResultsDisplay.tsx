"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { HypothesisOutput } from "@/lib/types";
import { IdeaCard } from "@/components/IdeaCard";

interface ResultsDisplayProps {
  hypothesis: HypothesisOutput | null;
  reportContent: string | null;
}

export function ResultsDisplay({ hypothesis, reportContent }: ResultsDisplayProps) {
  if (!hypothesis && !reportContent) {
    return (
      <Card className="border-border">
        <CardContent className="p-8 text-center text-muted-foreground">
          Results will appear here after analysis completes.
        </CardContent>
      </Card>
    );
  }

  return (
    <Tabs defaultValue="ideas" className="w-full">
      <TabsList>
        <TabsTrigger value="ideas">
          Business Ideas {hypothesis ? `(${hypothesis.ideas.length})` : ""}
        </TabsTrigger>
        <TabsTrigger value="report">
          Report
        </TabsTrigger>
      </TabsList>

      <TabsContent value="ideas">
        {hypothesis ? (
          <div className="space-y-4 mt-4">
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
        ) : (
          <div className="text-muted-foreground text-center py-8">
            No hypothesis data available.
          </div>
        )}
      </TabsContent>

      <TabsContent value="report">
        {reportContent ? (
          <ScrollArea className="h-[600px]">
            <div className="prose prose-invert prose-sm max-w-none mt-4 whitespace-pre-wrap">
              {reportContent}
            </div>
          </ScrollArea>
        ) : (
          <div className="text-muted-foreground text-center py-8">
            No report available.
          </div>
        )}
      </TabsContent>
    </Tabs>
  );
}
