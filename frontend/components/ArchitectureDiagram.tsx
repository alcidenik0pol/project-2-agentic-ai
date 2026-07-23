"use client";

import type { DataSource } from "@/lib/types";

// Preprocessing box — swaps the first pipeline stage per data source.
const ARCH_PREPROCESSING: Record<DataSource, { title: string; subtitle: string }> = {
  reddit_live: {
    title: "Subreddit Selection",
    subtitle:
      "LLM selects relevant subreddits from curated knowledge base (fallback: keyword matching)",
  },
  reddit_v2: {
    title: "Subreddit Selection",
    subtitle:
      "LLM selects relevant subreddits from curated knowledge base (same as reddit_live)",
  },
  reddit_v3: {
    title: "Subreddit Selection",
    subtitle:
      "LLM selects relevant subreddits from curated knowledge base (same as reddit_live/v2)",
  },
  pushshift: {
    title: "Dataset: Pushshift Archive (HuggingFace)",
    subtitle:
      "fddemarco/pushshift-reddit — RS_2018-01_00.parquet (Jan 2018, 11.3M submissions / 241K subs). DuckDB SQL on title, score≥1, top 100.",
  },
  linanqiu: {
    title: "Dataset: Linanqiu Reddit Dataset",
    subtitle:
      "Local JSON (~10,170 posts / 51 subs, Feb 2016). In-memory keyword filter on title or body, ups≥1, top 100.",
  },
  sample_default: {
    title: "Dataset: Sample Posts",
    subtitle:
      "data/smallsample/sample_posts.json — 30 posts across r/antiwork, r/personalfinance, r/ADHD (Apr 2026). Whole file loaded.",
  },
  sample_gaming: {
    title: "Dataset: Sample Gaming",
    subtitle:
      "data/smallsample/gaming_test_20260416_105527.json — 4 gaming subs (Apr 2026). Whole file loaded.",
  },
};

// Orchestrator tool label — swaps the tool description per data source.
const ARCH_LABELS: Record<DataSource, string> = {
  reddit_live: "Tool: fetch_posts (Reddit API OAuth)",
  reddit_v2: "Tool: fetch_posts (old.reddit.com HTML scraper)",
  reddit_v3: "Tool: fetch_posts (www.reddit.com Atom RSS scraper)",
  pushshift: "Tool: fetch_posts (DuckDB SQL on Parquet)",
  linanqiu: "Tool: fetch_posts (in-memory JSON filter)",
  sample_default: "Tool: fetch_posts (static JSON load)",
  sample_gaming: "Tool: fetch_posts (static JSON load)",
};

export function ArchitectureDiagram({ dataSource }: { dataSource: DataSource }) {
  const preprocessing = ARCH_PREPROCESSING[dataSource];
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

        {/* Preprocessing / dataset selection (source-specific) */}
        <div className="bg-secondary border border-border px-6 py-2 w-full max-w-md">
          <div className="font-medium mb-1 text-foreground">{preprocessing.title}</div>
          <div className="text-muted-foreground text-[10px]">
            {preprocessing.subtitle}
          </div>
        </div>

        <svg width="2" height="12"><line x1="1" y1="0" x2="1" y2="12" stroke="currentColor" className="text-muted-foreground" /></svg>

        {/* Orchestrator */}
        <div className="bg-secondary border border-border px-6 py-2 w-full max-w-md">
          <div className="font-medium mb-1 text-foreground">Orchestrator Agent</div>
          <div className="text-muted-foreground text-[10px]">
            {ARCH_LABELS[dataSource]}
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
