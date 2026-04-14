"use client";

export function ArchitectureDiagram() {
  return (
    <div className="space-y-2">
      <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
        System Architecture
      </div>
      <div className="flex flex-col items-center gap-3 text-xs">
        {/* User */}
        <div className="bg-secondary border border-border px-6 py-2 text-foreground font-medium">
          User Query
        </div>

        <svg width="2" height="12"><line x1="1" y1="0" x2="1" y2="12" stroke="currentColor" className="text-muted-foreground" /></svg>

        {/* Subreddit Selection */}
        <div className="bg-secondary border border-border px-6 py-2 w-full max-w-md">
          <div className="font-medium mb-1 text-foreground">Subreddit Selection</div>
          <div className="text-muted-foreground text-[10px]">
            LLM selects relevant subreddits from curated knowledge base (fallback: keyword matching)
          </div>
        </div>

        <svg width="2" height="12"><line x1="1" y1="0" x2="1" y2="12" stroke="currentColor" className="text-muted-foreground" /></svg>

        {/* Orchestrator */}
        <div className="bg-secondary border border-border px-6 py-2 w-full max-w-md">
          <div className="font-medium mb-1 text-foreground">Orchestrator Agent</div>
          <div className="text-muted-foreground text-[10px]">
            Tool: fetch_posts (Reddit API OAuth)
          </div>
        </div>

        <svg width="2" height="12"><line x1="1" y1="0" x2="1" y2="12" stroke="currentColor" className="text-muted-foreground" /></svg>

        {/* Analyst */}
        <div className="bg-secondary border border-border px-6 py-2 w-full max-w-md">
          <div className="font-medium mb-1 text-foreground">Analyst Agent</div>
          <div className="text-muted-foreground text-[10px] space-y-0.5">
            <div>1. classify_posts &rarr; per-post LLM calls (theme + intensity)</div>
            <div>2. expand_themes &rarr; batch LLM calls for richer descriptions</div>
            <div>3. embed &amp; cluster &rarr; embeddings + KMeans</div>
            <div>4. cluster_themes &rarr; per-cluster LLM naming</div>
          </div>
        </div>

        <svg width="2" height="12"><line x1="1" y1="0" x2="1" y2="12" stroke="currentColor" className="text-muted-foreground" /></svg>

        {/* Hypothesis */}
        <div className="bg-secondary border border-border px-6 py-2 w-full max-w-md">
          <div className="font-medium mb-1 text-foreground">Hypothesis Agent</div>
          <div className="text-muted-foreground text-[10px]">
            Tools: generate_hypotheses (structured LLM), save_artifact
          </div>
        </div>

        <svg width="2" height="12"><line x1="1" y1="0" x2="1" y2="12" stroke="currentColor" className="text-muted-foreground" /></svg>

        {/* Output */}
        <div className="bg-secondary border border-border px-6 py-2 text-foreground font-medium">
          Ranked Business Ideas + Report
        </div>

        {/* Data flow note */}
        <div className="mt-3 text-[10px] text-muted-foreground text-center max-w-sm">
          Data flows between agents via a shared store persisted to disk.
          Each agent has distinct tools and system prompts.
          8 total LLM call types across the pipeline.
        </div>
      </div>
    </div>
  );
}
