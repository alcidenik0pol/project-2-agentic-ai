"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";
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
}

export function TabbedResultsDisplay({
  hypothesis,
  classificationEDA,
  clusteringEDA,
}: TabbedResultsDisplayProps) {
  if (!hypothesis && !classificationEDA && !clusteringEDA) {
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
      <TabsList className="grid w-full grid-cols-3">
        <TabsTrigger value="ideas">
          Business Ideas
        </TabsTrigger>
        <TabsTrigger value="classification" disabled={!classificationEDA}>
          Classification EDA
        </TabsTrigger>
        <TabsTrigger value="clustering" disabled={!clusteringEDA}>
          Clustering Results
        </TabsTrigger>
      </TabsList>

      <TabsContent value="ideas" className="space-y-4 mt-4">
        {hypothesis ? (
          <>
            {hypothesis.analysis_summary && (
              <p className="text-sm text-muted-foreground">
                {hypothesis.analysis_summary}
              </p>
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
        ) : (
          <Card className="border-border">
            <CardContent className="p-8 text-center text-muted-foreground">
              Business ideas will appear here after analysis completes.
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
              Classification EDA will appear here after the analyst agent completes.
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
              Clustering results will appear here after the analyst agent completes.
            </CardContent>
          </Card>
        )}
      </TabsContent>
    </Tabs>
  );
}
