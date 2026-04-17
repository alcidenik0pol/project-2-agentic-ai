"use client";

import { AgentFlow } from "@/components/AgentFlow";
import { ArchitectureDiagram } from "@/components/ArchitectureDiagram";
import { useGlobalWebSocket } from "@/hooks/useGlobalWebSocket";
import { ChevronDown } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

const SUBREDDIT_GROUPS: { domain: string; subs: { name: string; url: string }[] }[] = [
  {
    domain: "Finance & Money",
    subs: [
      { name: "r/personalfinance", url: "https://reddit.com/r/personalfinance" },
      { name: "r/povertyfinance", url: "https://reddit.com/r/povertyfinance" },
      { name: "r/debtfree", url: "https://reddit.com/r/debtfree" },
      { name: "r/leanfire", url: "https://reddit.com/r/leanfire" },
      { name: "r/fatFIRE", url: "https://reddit.com/r/fatFIRE" },
      { name: "r/studentloans", url: "https://reddit.com/r/studentloans" },
      { name: "r/antiwork", url: "https://reddit.com/r/antiwork" },
      { name: "r/almosthomeless", url: "https://reddit.com/r/almosthomeless" },
      { name: "r/breakingmom", url: "https://reddit.com/r/breakingmom" },
      { name: "r/realestateinvesting", url: "https://reddit.com/r/realestateinvesting" },
    ],
  },
  {
    domain: "Work & Career",
    subs: [
      { name: "r/jobs", url: "https://reddit.com/r/jobs" },
      { name: "r/recruitinghell", url: "https://reddit.com/r/recruitinghell" },
      { name: "r/cscareerquestions", url: "https://reddit.com/r/cscareerquestions" },
      { name: "r/workreform", url: "https://reddit.com/r/workreform" },
      { name: "r/careerguidance", url: "https://reddit.com/r/careerguidance" },
      { name: "r/whitecollar", url: "https://reddit.com/r/whitecollar" },
      { name: "r/productivity", url: "https://reddit.com/r/productivity" },
      { name: "r/selfhosted", url: "https://reddit.com/r/selfhosted" },
      { name: "r/entrepreneur", url: "https://reddit.com/r/entrepreneur" },
      { name: "r/software", url: "https://reddit.com/r/software" },
      { name: "r/smallbusiness", url: "https://reddit.com/r/smallbusiness" },
      { name: "r/freelance", url: "https://reddit.com/r/freelance" },
      { name: "r/consulting", url: "https://reddit.com/r/consulting" },
    ],
  },
  {
    domain: "Relationships & Dating",
    subs: [
      { name: "r/relationship_advice", url: "https://reddit.com/r/relationship_advice" },
      { name: "r/relationships", url: "https://reddit.com/r/relationships" },
      { name: "r/amitheasshole", url: "https://reddit.com/r/amitheasshole" },
      { name: "r/breakups", url: "https://reddit.com/r/breakups" },
      { name: "r/lonely", url: "https://reddit.com/r/lonely" },
      { name: "r/dating", url: "https://reddit.com/r/dating" },
      { name: "r/datingoverthirty", url: "https://reddit.com/r/datingoverthirty" },
      { name: "r/deadbedrooms", url: "https://reddit.com/r/deadbedrooms" },
    ],
  },
  {
    domain: "Parenting",
    subs: [
      { name: "r/daddit", url: "https://reddit.com/r/daddit" },
      { name: "r/beyondthebump", url: "https://reddit.com/r/beyondthebump" },
      { name: "r/parenting", url: "https://reddit.com/r/parenting" },
      { name: "r/mommit", url: "https://reddit.com/r/mommit" },
    ],
  },
  {
    domain: "Health & Psychology",
    subs: [
      { name: "r/depression", url: "https://reddit.com/r/depression" },
      { name: "r/anxiety", url: "https://reddit.com/r/anxiety" },
      { name: "r/ADHD", url: "https://reddit.com/r/ADHD" },
      { name: "r/offmychest", url: "https://reddit.com/r/offmychest" },
      { name: "r/trueoffmychest", url: "https://reddit.com/r/trueoffmychest" },
      { name: "r/therapy", url: "https://reddit.com/r/therapy" },
      { name: "r/socialanxiety", url: "https://reddit.com/r/socialanxiety" },
      { name: "r/insomnia", url: "https://reddit.com/r/insomnia" },
      { name: "r/chronicpain", url: "https://reddit.com/r/chronicpain" },
      { name: "r/chronicillness", url: "https://reddit.com/r/chronicillness" },
      { name: "r/ehlersdanlos", url: "https://reddit.com/r/ehlersdanlos" },
      { name: "r/PCOS", url: "https://reddit.com/r/PCOS" },
      { name: "r/GERD", url: "https://reddit.com/r/GERD" },
      { name: "r/Menopause", url: "https://reddit.com/r/Menopause" },
      { name: "r/Fibromyalgia", url: "https://reddit.com/r/Fibromyalgia" },
      { name: "r/diabetes", url: "https://reddit.com/r/diabetes" },
      { name: "r/diabetes_t2", url: "https://reddit.com/r/diabetes_t2" },
    ],
  },
  {
    domain: "Housing & Cost of Living",
    subs: [
      { name: "r/FirstTimeHomeBuyer", url: "https://reddit.com/r/FirstTimeHomeBuyer" },
      { name: "r/renting", url: "https://reddit.com/r/renting" },
      { name: "r/malelivingspace", url: "https://reddit.com/r/malelivingspace" },
      { name: "r/fuckcars", url: "https://reddit.com/r/fuckcars" },
    ],
  },
  {
    domain: "Life Stage & Identity",
    subs: [
      { name: "r/adulting", url: "https://reddit.com/r/adulting" },
      { name: "r/quarterlifecrisis", url: "https://reddit.com/r/quarterlifecrisis" },
      { name: "r/midlifecrisis", url: "https://reddit.com/r/midlifecrisis" },
      { name: "r/ChildFree", url: "https://reddit.com/r/ChildFree" },
      { name: "r/30PlusSkinCare", url: "https://reddit.com/r/30PlusSkinCare" },
      { name: "r/malementalhealth", url: "https://reddit.com/r/malementalhealth" },
    ],
  },
  {
    domain: "Caregiving",
    subs: [
      { name: "r/AgingParents", url: "https://reddit.com/r/AgingParents" },
      { name: "r/dementia", url: "https://reddit.com/r/dementia" },
      { name: "r/caregiver", url: "https://reddit.com/r/caregiver" },
    ],
  },
  {
    domain: "Immigration & Legal",
    subs: [
      { name: "r/immigration", url: "https://reddit.com/r/immigration" },
      { name: "r/USCIS", url: "https://reddit.com/r/USCIS" },
      { name: "r/f1visa", url: "https://reddit.com/r/f1visa" },
    ],
  },
  {
    domain: "Consumer Frustration",
    subs: [
      { name: "r/mildlyinfuriating", url: "https://reddit.com/r/mildlyinfuriating" },
      { name: "r/assholedesign", url: "https://reddit.com/r/assholedesign" },
      { name: "r/softwaregore", url: "https://reddit.com/r/softwaregore" },
      { name: "r/talesfromtechsupport", url: "https://reddit.com/r/talesfromtechsupport" },
    ],
  },
  {
    domain: "Entertainment",
    subs: [
      { name: "r/patientgamers", url: "https://reddit.com/r/patientgamers" },
      { name: "r/gaming", url: "https://reddit.com/r/gaming" },
      { name: "r/gameideas", url: "https://reddit.com/r/gameideas" },
      { name: "r/gamedev", url: "https://reddit.com/r/gamedev" },
      { name: "r/pcgaming", url: "https://reddit.com/r/pcgaming" },
      { name: "r/Steam", url: "https://reddit.com/r/Steam" },
      { name: "r/indiegaming", url: "https://reddit.com/r/indiegaming" },
      { name: "r/television", url: "https://reddit.com/r/television" },
      { name: "r/cordcutters", url: "https://reddit.com/r/cordcutters" },
      { name: "r/streamingwars", url: "https://reddit.com/r/streamingwars" },
      { name: "r/moviesuggestions", url: "https://reddit.com/r/moviesuggestions" },
      { name: "r/spotify", url: "https://reddit.com/r/spotify" },
      { name: "r/vinyl", url: "https://reddit.com/r/vinyl" },
      { name: "r/WeAreTheMusicMakers", url: "https://reddit.com/r/WeAreTheMusicMakers" },
      { name: "r/suggestmeabook", url: "https://reddit.com/r/suggestmeabook" },
      { name: "r/kindle", url: "https://reddit.com/r/kindle" },
      { name: "r/Audiobooks", url: "https://reddit.com/r/Audiobooks" },
    ],
  },
];

export default function HowItWorksPage() {
  const { agents } = useGlobalWebSocket();
  const [subredditListOpen, setSubredditListOpen] = useState(false);

  return (
    <div className="flex flex-col items-center px-4 py-8">
      <div className="w-full max-w-3xl">
        <h1 className="text-lg font-bold mb-1">How It Works</h1>
        <p className="text-xs text-muted-foreground mb-8">
          A multi-agent pipeline with 8 distinct LLM call types that discovers
          unsolved pain points on Reddit. A preprocessing step selects relevant
          subreddits, then three agents — Orchestrator, Analyst, and Hypothesis
          — process the data through classification, embedding, clustering, and
          hypothesis generation.
        </p>

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
            <ArchitectureDiagram />
          </div>
        </section>

        {/* Preprocessing */}
        <section className="mb-8 space-y-6">
          <h2 className="text-sm font-medium">How the system works</h2>

          <div className="border border-border bg-card p-4 space-y-2">
            <h3 className="text-xs font-medium text-foreground">
              Preprocessing: Subreddit Selection (Call 8)
            </h3>
            <p className="text-xs text-muted-foreground">
              Before any agent runs, the system selects relevant subreddits from a
              curated knowledge base. An LLM call (<code className="bg-secondary px-1">generate_structured</code>)
              ranks subreddits by relevance to the user&apos;s topic. Falls back to
              keyword-based matching if the LLM call fails.
            </p>
            <p className="text-[10px] text-muted-foreground">
              Source: <code className="bg-secondary px-1">app/collector/subreddit_selector.py:119</code>
            </p>
          </div>

          <div className="border border-border bg-card p-4 space-y-2">
            <h3 className="text-xs font-medium text-foreground">
              Agent 1: Orchestrator (Call 1)
            </h3>
            <p className="text-xs text-muted-foreground">
              Takes the user&apos;s topic and uses the <code className="bg-secondary px-1">fetch_posts</code> tool
              to gather Reddit posts from the pre-selected subreddits via the Reddit API (OAuth).
              Fetches both complaints and expressed desires/gaps, then hands off to the Analyst
              with a summary of what was collected.
            </p>
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
              The Reddit API is not called twice for the same topic. First results are stored and reused.
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
                  <td className="py-1">Preprocessing: select relevant subreddits</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        {/* Subreddit Knowledge Base */}
        <section className="mb-8">
          <button
            onClick={() => setSubredditListOpen((prev) => !prev)}
            className="w-full flex items-center justify-between text-sm font-medium hover:text-foreground/80 transition-colors"
          >
            <span>Subreddit Knowledge Base ({SUBREDDIT_GROUPS.reduce((acc, g) => acc + g.subs.length, 0)} subreddits)</span>
            <ChevronDown
              className={`h-4 w-4 transition-transform ${subredditListOpen ? "rotate-180" : ""}`}
            />
          </button>

          {subredditListOpen && (
            <div className="mt-3 border border-border bg-card p-4 space-y-4">
              <p className="text-[10px] text-muted-foreground">
                Curated subreddits used by the preprocessing step (Call 8) to select
                relevant sources for a given topic.
              </p>
              {SUBREDDIT_GROUPS.map((group) => (
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
              ))}
            </div>
          )}
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
