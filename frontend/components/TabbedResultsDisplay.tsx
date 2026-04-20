"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";
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

export function TabbedResultsDisplay({
  hypothesis,
  classificationEDA,
  clusteringEDA,
  query,
  generationComplete,
}: TabbedResultsDisplayProps) {
  if (!hypothesis && !classificationEDA && !clusteringEDA) {
    return null;
  }

  return (
    <Tabs defaultValue="ideas" className="w-full">
      {/* Vertical on mobile, horizontal on desktop */}
      <div className="flex flex-col sm:block">
        <TabsList className="flex flex-col sm:grid sm:grid-cols-3 w-full h-auto sm:h-10 gap-1">
          <TabsTrigger value="ideas">
            The Gold
            {hypothesis && <Check className="w-4 h-4 ml-2 text-green-500" strokeWidth={3} />}
          </TabsTrigger>
          <TabsTrigger value="classification" disabled={!classificationEDA}>
            Classification EDA
            {classificationEDA && <Check className="w-4 h-4 ml-2 text-green-500" strokeWidth={3} />}
          </TabsTrigger>
          <TabsTrigger value="clustering" disabled={!clusteringEDA}>
            Clustering Results
            {clusteringEDA && <Check className="w-4 h-4 ml-2 text-green-500" strokeWidth={3} />}
          </TabsTrigger>
        </TabsList>
      </div>

      <TabsContent value="ideas" className="space-y-4 mt-4">
        {hypothesis ? (
          <>
            {hypothesis.analysis_summary && (
              <div className="text-sm text-muted-foreground">
                {query && (
                  <span className="font-medium text-foreground">
                    Here's what people can't stop complaining about in {query}:
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
          <Card className="border-border">
            <CardContent className="p-8 text-center text-muted-foreground">
              No gold spotted. Try panning a different industry.
            </CardContent>
          </Card>
        ) : (
          <Card className="border-border">
            <CardContent className="p-8 text-center text-muted-foreground">
              Generating your opportunities report <span className="inline-flex animate-pulse">...</span>
            </CardContent>
          </Card>
        )}
      </TabsContent>

      <TabsContent value="classification" className="mt-4">
        {classificationEDA ? (
          <ClassificationEDATable data={classificationEDA} />
        ) : (
          <Card className="border-border">
            <CardContent className="p-8 text-center text-muted-foreground">
              Classification EDA appears after the analyst finishes digging.
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
              Clustering results appear after the analyst finishes digging.
            </CardContent>
          </Card>
        )}
      </TabsContent>
    </Tabs>
  );
}
