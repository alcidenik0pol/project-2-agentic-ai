"use client";

import { AgentFlow } from "@/components/AgentFlow";
import { ArchitectureDiagram } from "@/components/ArchitectureDiagram";
import { useGlobalWebSocket } from "@/hooks/useGlobalWebSocket";
import Link from "next/link";
import { useState } from "react";
import { useAnalysis } from "@/contexts/AnalysisContext";
import { DATA_SOURCES } from "@/lib/data-sources";
import { DATASET_CARDS } from "@/lib/datasets";
import type { DataSource } from "@/lib/types";

// ── Per-source prose ──
// intro / preprocessingCard / orchestratorCard vary by data source.
// FACTS (sizes, subreddit counts, vintage, etc.) live in frontend/lib/datasets.ts —
// do NOT duplicate numbers here.
//
// Common sections (AgentFlow, Analyst, Hypothesis, LLM calls table) are unchanged.

interface SourceContent {
  intro: string;
  preprocessingCard: {
    title: string;
    body: React.ReactNode;
    sourceRef: string;
  };
  orchestratorCard: {
    body: React.ReactNode;
  };
}

const Code = ({ children }: { children: React.ReactNode }) => (
  <code className="bg-secondary px-1">{children}</code>
);

const SOURCE_CONTENT: Record<DataSource, SourceContent> = {
  reddit_live: {
    intro:
      "A multi-agent pipeline with 8 distinct LLM call types that discovers unsolved pain points on Reddit. A preprocessing step selects relevant subreddits, then three agents — Orchestrator, Analyst, and Hypothesis — process the data through classification, embedding, clustering, and hypothesis generation.",
    preprocessingCard: {
      title: "Preprocessing: Subreddit Selection (Call 8)",
      body: (
        <>
          Before any agent runs, the system selects relevant subreddits from a
          curated knowledge base. An LLM call (<Code>generate_structured</Code>)
          ranks subreddits by relevance to the user&apos;s topic. Falls back to
          keyword-based matching if the LLM call fails.
        </>
      ),
      sourceRef: "app/collector/subreddit_selector.py:119",
    },
    orchestratorCard: {
      body: (
        <>
          Takes the user&apos;s topic and uses the <Code>fetch_posts</Code> tool
          to gather Reddit posts from the pre-selected subreddits via the Reddit API (OAuth).
          Fetches both complaints and expressed desires/gaps, then hands off to the Analyst
          with a summary of what was collected.
        </>
      ),
    },
  },
  reddit_v2: {
    intro:
      "A multi-agent pipeline with 8 distinct LLM call types that discovers unsolved pain points on Reddit. A preprocessing step selects relevant subreddits, then three agents — Orchestrator, Analyst, and Hypothesis — process the data through classification, embedding, clustering, and hypothesis generation. Posts are scraped from old.reddit.com HTML (Reddit killed the .json endpoints the legacy scraper depended on).",
    preprocessingCard: {
      title: "Preprocessing: Subreddit Selection (Call 8)",
      body: (
        <>
          Same as Reddit Live: an LLM call (<Code>generate_structured</Code>)
          ranks subreddits from the curated knowledge base by relevance to the
          user&apos;s topic. Falls back to keyword matching if the LLM call fails.
        </>
      ),
      sourceRef: "app/collector/subreddit_selector.py:119",
    },
    orchestratorCard: {
      body: (
        <>
          Takes the user&apos;s topic and uses the <Code>fetch_posts</Code> tool
          to scrape posts from the pre-selected subreddits via old.reddit.com HTML.
          Hands off the collected posts to the Analyst with a summary.
        </>
      ),
    },
  },
  reddit_v3: {
    intro:
      "A multi-agent pipeline with 8 distinct LLM call types that discovers unsolved pain points on Reddit. A preprocessing step selects relevant subreddits, then three agents — Orchestrator, Analyst, and Hypothesis — process the data through classification, embedding, clustering, and hypothesis generation. Posts are scraped from www.reddit.com Atom RSS feeds (Reddit enforced a sitewide login wall on old.reddit.com and 403'd all .json endpoints in July 2026).",
    preprocessingCard: {
      title: "Preprocessing: Subreddit Selection (Call 8)",
      body: (
        <>
          Same as Reddit Live: an LLM call (<Code>generate_structured</Code>)
          ranks subreddits from the curated knowledge base by relevance to the
          user&apos;s topic. Falls back to keyword matching if the LLM call fails.
        </>
      ),
      sourceRef: "app/collector/subreddit_selector.py:119",
    },
    orchestratorCard: {
      body: (
        <>
          Takes the user&apos;s topic and uses the <Code>fetch_posts</Code> tool
          to scrape posts from the pre-selected subreddits via www.reddit.com Atom
          RSS feeds (the only unauthenticated public surface left after Reddit&apos;s
          July 2026 login wall). Hands off the collected posts to the Analyst with
          a summary.
        </>
      ),
    },
  },
  pushshift: {
    intro:
      "A multi-agent pipeline with 8 distinct LLM call types that discovers unsolved pain points from historical Reddit data. A single Parquet shard from the Pushshift archive (HuggingFace, January 2018) is queried via DuckDB SQL, then three agents — Orchestrator, Analyst, and Hypothesis — process the data through classification, embedding, clustering, and hypothesis generation.",
    preprocessingCard: {
      title: "Data Source: Pushshift Archive (HuggingFace)",
      body: (
        <>
          Posts are drawn from <Code>fddemarco/pushshift-reddit</Code> on HuggingFace
          — specifically the single January 2018 shard (<Code>RS_2018-01_00.parquet</Code>).
          DuckDB runs SQL over the Parquet file — filtering on the <Code>title</Code>{" "}
          column, <Code>score &ge; 1</Code>, and returning the top 100 matches for the
          topic. The Parquet file is cached locally in <Code>data/hf_cache/</Code> after
          first download. No comments are available in this dataset.
        </>
      ),
      sourceRef: "app/pushshift/ (DuckDB on Parquet)",
    },
    orchestratorCard: {
      body: (
        <>
          Takes the user&apos;s topic and uses the <Code>fetch_posts</Code> tool
          to query the cached Parquet snapshot via DuckDB SQL. Filters titles by
          keyword, applies <Code>score &ge; 1</Code>, and returns the top 100 posts.
          Hands off the collected posts to the Analyst with a summary.
        </>
      ),
    },
  },
  linanqiu: {
    intro:
      "A multi-agent pipeline with 8 distinct LLM call types that discovers unsolved pain points from historical Reddit data. The Linanqiu dataset (~10,170 posts across 51 subreddits, February 2016) is filtered in memory, then three agents — Orchestrator, Analyst, and Hypothesis — process the data through classification, embedding, clustering, and hypothesis generation.",
    preprocessingCard: {
      title: "Data Source: Linanqiu Reddit Dataset",
      body: (
        <>
          Posts are drawn from a local JSON export of the Linanqiu Reddit dataset
          (github.com/linanqiu/reddit-dataset, ~10,170 posts / 51 subreddits,
          February 2016). The Orchestrator filters posts in memory by keyword on
          the title OR body, applies <Code>ups &ge; 1</Code>, and returns the top 100.
          Post titles are synthesized where missing. No comments are available in
          this dataset.
        </>
      ),
      sourceRef: "data/linanqiu/ (local JSON)",
    },
    orchestratorCard: {
      body: (
        <>
          Takes the user&apos;s topic and uses the <Code>fetch_posts</Code> tool
          to filter the local Linanqiu JSON in memory. Matches keyword against
          title or body, applies <Code>ups &ge; 1</Code>, and returns the top 100
          posts. Hands off the collected posts to the Analyst with a summary.
        </>
      ),
    },
  },
  sample_default: {
    intro:
      "A multi-agent pipeline with 8 distinct LLM call types that discovers unsolved pain points from a small sample dataset. 30 posts from r/antiwork, r/personalfinance, and r/ADHD (April 2026) are loaded from a static JSON file, then three agents — Orchestrator, Analyst, and Hypothesis — process the data through classification, embedding, clustering, and hypothesis generation.",
    preprocessingCard: {
      title: "Data Source: Sample Dataset (3 subs)",
      body: (
        <>
          Posts are loaded from <Code>data/smallsample/sample_posts.json</Code> —
          30 posts across r/antiwork, r/personalfinance, and r/ADHD (April 2026).
          The entire file is loaded; no keyword filtering or score threshold is
          applied. No comments are available in this dataset.
        </>
      ),
      sourceRef: "data/smallsample/sample_posts.json",
    },
    orchestratorCard: {
      body: (
        <>
          Takes the user&apos;s topic and uses the <Code>fetch_posts</Code> tool
          to load the entire <Code>sample_posts.json</Code> file. No filtering is
          applied; all 30 posts are handed to the Analyst with a summary.
        </>
      ),
    },
  },
  sample_gaming: {
    intro:
      "A multi-agent pipeline with 8 distinct LLM call types that discovers unsolved pain points from a small gaming sample dataset. 36 posts across 4 gaming subreddits (April 2026) are loaded from a static JSON file, then three agents — Orchestrator, Analyst, and Hypothesis — process the data through classification, embedding, clustering, and hypothesis generation.",
    preprocessingCard: {
      title: "Data Source: Sample Gaming (4 subs)",
      body: (
        <>
          Posts are loaded from <Code>data/smallsample/gaming_test_20260416_105527.json</Code> —
          36 posts across 4 gaming subreddits (April 2026). The entire file is
          loaded; no keyword filtering or score threshold is applied. No comments
          are available in this dataset.
        </>
      ),
      sourceRef: "data/smallsample/gaming_test_20260416_105527.json",
    },
    orchestratorCard: {
      body: (
        <>
          Takes the user&apos;s topic and uses the <Code>fetch_posts</Code> tool
          to load the entire gaming test JSON file. No filtering is applied; all
          posts are handed to the Analyst with a summary.
        </>
      ),
    },
  },
};

export default function HowItWorksPage() {
  const { agents } = useGlobalWebSocket();
  const { dataSource: globalDataSource } = useAnalysis();
  // One-way sync: seed from the home-page selection on mount; local changes do
  // NOT propagate back. Re-mounting (navigation) re-seeds.
  const [selectedSource, setSelectedSource] = useState<DataSource>(globalDataSource);

  const content = SOURCE_CONTENT[selectedSource];
  const card = DATASET_CARDS[selectedSource];
  // Live sources use the curated KB + preprocessing (Call 8). Offline sources
  // load their whole dataset at runtime.
  const isLive =
    selectedSource === "reddit_live" ||
    selectedSource === "reddit_v2" ||
    selectedSource === "reddit_v3";
  const subredditCount = card.subredditGroups.reduce((acc, g) => acc + g.subs.length, 0);

  return (
    <div className="flex flex-col items-center px-4 py-8">
      <div className="w-full max-w-3xl">
        <h1 className="text-lg font-bold mb-1">How It Works</h1>

        {/* Data source selector — seeds from home page, does not write back */}
        <div className="flex items-center gap-2 mb-4">
          <label htmlFor="hiw-source" className="text-xs text-muted-foreground">
            Data source:
          </label>
          <select
            id="hiw-source"
            value={selectedSource}
            onChange={(e) => setSelectedSource(e.target.value as DataSource)}
            className="h-7 px-2 rounded text-xs bg-background text-foreground border border-border focus:outline-none focus:ring-1 focus:ring-ring cursor-pointer"
          >
            {DATA_SOURCES.map((ds) => (
              <option key={ds.value} value={ds.value} className="bg-background text-foreground">
                {ds.label}
              </option>
            ))}
          </select>
        </div>

        <p className="text-xs text-muted-foreground mb-8">{content.intro}</p>

        {/* Agent Pipeline - live if analysis is running */}
        <section className="mb-8">
          <h2 className="text-sm font-medium mb-4">Agent Pipeline</h2>
          <div className="border border-border bg-card p-6">
            <AgentFlow agents={agents} />
            <p className="text-[10px] text-muted-foreground mt-4 text-center">
              {agents.some((a) => a.status !== "idle")
                ? "Showing live agent status from current analysis"
                : "Start an analysis on the home page to see live agent progress"}
            </p>
          </div>
        </section>

        {/* Architecture Diagram */}
        <section className="mb-8">
          <h2 className="text-sm font-medium mb-4">System Architecture</h2>
          <div className="border border-border bg-card p-6">
            <ArchitectureDiagram dataSource={selectedSource} />
          </div>
        </section>

        {/* Preprocessing */}
        <section className="mb-8 space-y-6">
          <h2 className="text-sm font-medium">How the system works</h2>

          <div className="border border-border bg-card p-4 space-y-2">
            <h3 className="text-xs font-medium text-foreground">
              {content.preprocessingCard.title}
            </h3>
            <p className="text-xs text-muted-foreground">{content.preprocessingCard.body}</p>
            <p className="text-[10px] text-muted-foreground">
              Source: <code className="bg-secondary px-1">{content.preprocessingCard.sourceRef}</code>
            </p>
          </div>

          <div className="border border-border bg-card p-4 space-y-2">
            <h3 className="text-xs font-medium text-foreground">
              Agent 1: Orchestrator (Call 1)
            </h3>
            <p className="text-xs text-muted-foreground">{content.orchestratorCard.body}</p>
            <p className="text-[10px] text-muted-foreground">
              Tools: <code className="bg-secondary px-1">fetch_posts</code>
              {" "}&middot; Source: <code className="bg-secondary px-1">app/agents/orchestrator.py</code>
            </p>
          </div>

          <div className="border border-border bg-card p-4 space-y-2">
            <h3 className="text-xs font-medium text-foreground">
              Agent 2: Analyst (Calls 2, 4, 5, 6)
            </h3>
            <p className="text-xs text-muted-foreground">
              Takes raw posts from the Orchestrator and processes them through
              a multi-step analysis pipeline:
            </p>
            <ol className="text-xs text-muted-foreground list-decimal list-inside space-y-1 pl-2">
              <li>
                <strong className="text-foreground">Classify</strong> (Call 4):
                Each post is classified by an LLM to extract its complaint theme,
                whether it is a complaint, and its intensity (low/medium/high).
              </li>
              <li>
                <strong className="text-foreground">Expand themes</strong> (Call 5):
                Short theme labels are expanded into 10-20 word descriptions
                (in batches of ~5) for better embedding quality.
              </li>
              <li>
                <strong className="text-foreground">Embed &amp; cluster</strong>:
                Expanded themes are converted to embeddings, then grouped via
                KMeans clustering.
              </li>
              <li>
                <strong className="text-foreground">Name clusters</strong> (Call 6):
                Each cluster receives a human-readable name generated by the LLM.
              </li>
            </ol>
            <p className="text-[10px] text-muted-foreground">
              Tools: <code className="bg-secondary px-1">classify_posts</code>{" "}
              <code className="bg-secondary px-1">cluster_themes</code>
              {" "}&middot; Source: <code className="bg-secondary px-1">app/agents/analyst.py</code>
            </p>
          </div>

          <div className="border border-border bg-card p-4 space-y-2">
            <h3 className="text-xs font-medium text-foreground">
              Agent 3: Hypothesis (Calls 3, 7)
            </h3>
            <p className="text-xs text-muted-foreground">
              Takes ranked clusters from the Analyst and generates up to 5 concrete
              business hypotheses. Each hypothesis includes:
            </p>
            <ul className="text-xs text-muted-foreground list-disc list-inside pl-2 space-y-0.5">
              <li><code className="bg-secondary px-1">idea_name</code> — concrete product name</li>
              <li><code className="bg-secondary px-1">pain_point</code> — specific frustration quoted from posts</li>
              <li><code className="bg-secondary px-1">solution_description</code> — specific features and user flows</li>
              <li><code className="bg-secondary px-1">core_features</code> — 3 to 5 tangible features</li>
              <li><code className="bg-secondary px-1">revenue_model</code> — explicit pricing or monetization</li>
              <li><code className="bg-secondary px-1">first_user_step</code> — what the user does in the first 30 seconds</li>
              <li><code className="bg-secondary px-1">target_user</code> — specific persona</li>
              <li><code className="bg-secondary px-1">confidence</code> + <code className="bg-secondary px-1">confidence_reasoning</code></li>
              <li><code className="bg-secondary px-1">evidence</code> — cluster name, post count, total upvotes, supporting post titles</li>
            </ul>
            <p className="text-[10px] text-muted-foreground">
              Tools: <code className="bg-secondary px-1">generate_hypotheses</code>{" "}
              <code className="bg-secondary px-1">save_artifact</code>
              {" "}&middot; Source: <code className="bg-secondary px-1">app/agents/hypothesis.py</code>
            </p>
          </div>
        </section>

        <section className="mb-8">
          <h2 className="text-sm font-medium mb-3">Key design decisions</h2>
          <ul className="text-xs text-muted-foreground space-y-2 list-disc list-inside">
            <li>
              <strong className="text-foreground">Data via shared store, not LLM context:</strong>{" "}
              Agent results are persisted to disk and read by the next agent, preventing context overflow.
            </li>
            <li>
              <strong className="text-foreground">Every finding traces to a real Reddit post:</strong>{" "}
              The system does not generate complaints from model knowledge. All evidence includes
              supporting post titles.
            </li>
            <li>
              <strong className="text-foreground">Results are cached:</strong>{" "}
              {isLive
                ? "The Reddit API is not called twice for the same topic. First results are stored and reused."
                : "Queries are stateless for offline sources — the dataset is re-queried each run with no cache."}
            </li>
            <li>
              <strong className="text-foreground">Tool calling is agent-driven:</strong>{" "}
              Each agent decides which tools to invoke based on its current step, not automatic backend processing.
            </li>
            <li>
              <strong className="text-foreground">Low temperature for consistency:</strong>{" "}
              All LLM calls use temperature 0.1 to 0.3, ensuring reproducible classification and clustering.
            </li>
            <li>
              <strong className="text-foreground">Retry logic on parse failures:</strong>{" "}
              Classification and expansion calls retry with a stricter prompt if the LLM returns invalid JSON
              (up to <code className="bg-secondary px-1">gcloud_max_retries</code> attempts).
            </li>
            <li>
              <strong className="text-foreground">Provider abstraction:</strong>{" "}
              Three LLM providers supported via a single interface: Google Cloud (Gemini 2.5 Flash),
              LM Studio (local), and OpenAI-compatible Gemini. Selected at runtime via{" "}
              <code className="bg-secondary px-1">LLM_PROVIDER</code> env var.
            </li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-sm font-medium mb-3">LLM calls summary</h2>
          <div className="overflow-x-auto">
            <table className="text-[10px] w-full border-collapse">
              <thead>
                <tr className="border-b border-border text-left">
                  <th className="py-1 pr-3 text-muted-foreground font-medium">#</th>
                  <th className="py-1 pr-3 text-muted-foreground font-medium">Call</th>
                  <th className="py-1 pr-3 text-muted-foreground font-medium">Method</th>
                  <th className="py-1 pr-3 text-muted-foreground font-medium">Temp</th>
                  <th className="py-1 text-muted-foreground font-medium">Purpose</th>
                </tr>
              </thead>
              <tbody className="text-muted-foreground">
                <tr className="border-b border-border/50">
                  <td className="py-1 pr-3">1</td>
                  <td className="py-1 pr-3">Orchestrator Agent</td>
                  <td className="py-1 pr-3">chat_with_tools</td>
                  <td className="py-1 pr-3">0.3</td>
                  <td className="py-1">Agent loop: fetch Reddit posts</td>
                </tr>
                <tr className="border-b border-border/50">
                  <td className="py-1 pr-3">2</td>
                  <td className="py-1 pr-3">Analyst Agent</td>
                  <td className="py-1 pr-3">chat_with_tools</td>
                  <td className="py-1 pr-3">0.3</td>
                  <td className="py-1">Agent loop: classify &amp; cluster</td>
                </tr>
                <tr className="border-b border-border/50">
                  <td className="py-1 pr-3">3</td>
                  <td className="py-1 pr-3">Hypothesis Agent</td>
                  <td className="py-1 pr-3">chat_with_tools</td>
                  <td className="py-1 pr-3">0.3</td>
                  <td className="py-1">Agent loop: generate hypotheses</td>
                </tr>
                <tr className="border-b border-border/50">
                  <td className="py-1 pr-3">4</td>
                  <td className="py-1 pr-3">Post Classification</td>
                  <td className="py-1 pr-3">classify_post</td>
                  <td className="py-1 pr-3">0.1</td>
                  <td className="py-1">Per-post: theme, is_complaint, intensity</td>
                </tr>
                <tr className="border-b border-border/50">
                  <td className="py-1 pr-3">5</td>
                  <td className="py-1 pr-3">Theme Expansion</td>
                  <td className="py-1 pr-3">generate_text</td>
                  <td className="py-1 pr-3">0.3</td>
                  <td className="py-1">Per-batch: expand themes for embeddings</td>
                </tr>
                <tr className="border-b border-border/50">
                  <td className="py-1 pr-3">6</td>
                  <td className="py-1 pr-3">Cluster Naming</td>
                  <td className="py-1 pr-3">generate_text</td>
                  <td className="py-1 pr-3">0.3</td>
                  <td className="py-1">Per-cluster: human-readable name</td>
                </tr>
                <tr className="border-b border-border/50">
                  <td className="py-1 pr-3">7</td>
                  <td className="py-1 pr-3">Hypothesis Generation</td>
                  <td className="py-1 pr-3">generate_structured</td>
                  <td className="py-1 pr-3">0.3</td>
                  <td className="py-1">Top-5 business hypotheses (max 16,384 tokens)</td>
                </tr>
                <tr>
                  <td className="py-1 pr-3">8</td>
                  <td className="py-1 pr-3">Subreddit Selection</td>
                  <td className="py-1 pr-3">generate_structured</td>
                  <td className="py-1 pr-3">0.3</td>
                  <td className="py-1">
                    {isLive ? (
                      "Preprocessing: select relevant subreddits"
                    ) : (
                      <span className="italic text-muted-foreground/70">
                        Preprocessing: subreddit selection (live scrapers only — not invoked for this data source)
                      </span>
                    )}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        {/* Dataset Composition — always visible, all sources. Facts come from datasets.ts. */}
        <section className="mb-8">
          <h2 className="text-sm font-medium mb-3">Dataset Composition</h2>
          <div className="border border-border bg-card p-4">
            <p className="text-[10px] text-muted-foreground mb-3">
              Composition of the dataset used by{" "}
              <code className="bg-secondary px-1">{card.id}</code>
              {" "}({card.shortLabel}).
            </p>
            <table className="text-[10px] w-full border-collapse">
              <tbody>
                {card.facts.map((row) => (
                  <tr key={row.label} className="border-b border-border/50 last:border-0">
                    <td className="py-1 pr-3 text-muted-foreground font-medium align-top whitespace-nowrap">
                      {row.label}
                    </td>
                    <td className="py-1 text-foreground">{row.value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Subreddits — always visible, all sources. List comes from datasets.ts. */}
        <section className="mb-8">
          <h2 className="text-sm font-medium mb-3">
            {card.subredditGroups.length > 0
              ? isLive
                ? `Subreddit Knowledge Base (${subredditCount} subreddits)`
                : `Subreddits in Dataset (${subredditCount})`
              : isLive
                ? "Subreddit Knowledge Base"
                : "Subreddits in Dataset"}
          </h2>
          <div className="border border-border bg-card p-4 space-y-4">
            <p className="text-[10px] text-muted-foreground">{card.subredditBlurb}</p>
            {card.subredditGroups.length === 0 ? (
              <p className="text-[10px] italic text-muted-foreground/70">
                Not enumerated — see blurb above.
              </p>
            ) : (
              card.subredditGroups.map((group) => (
                <div key={group.domain}>
                  <h3 className="text-xs font-medium text-foreground mb-1.5">
                    {group.domain}
                  </h3>
                  <div className="flex flex-wrap gap-1.5">
                    {group.subs.map((sub) => (
                      <a
                        key={sub.name}
                        href={sub.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[10px] px-2 py-0.5 bg-secondary text-muted-foreground hover:text-foreground transition-colors"
                      >
                        {sub.name}
                      </a>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        <div className="mt-4">
          <Link
            href="/"
            className="text-xs text-muted-foreground hover:text-foreground transition-colors underline"
          >
            Back to Home
          </Link>
        </div>
      </div>
    </div>
  );
}
