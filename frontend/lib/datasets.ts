// ─────────────────────────────────────────────────────────────────────────────
// SINGLE SOURCE OF TRUTH for dataset metadata.
//
// To add/update a dataset, edit only this file. The dropdown labels, dataset
// composition table, and subreddit list on /how-it-works all read from here.
//
// DO NOT duplicate these facts elsewhere. If a number appears in the UI, it
// must trace back to an entry in DATASET_CARDS below.
// ─────────────────────────────────────────────────────────────────────────────

import type { DataSource } from "@/lib/types";

export interface SubredditGroup {
  domain: string;
  subs: { name: string; url: string }[];
}

export interface DatasetFact {
  label: string; // Display label in the composition table (e.g. "Source").
  value: string; // Value shown (e.g. "HuggingFace fddemarco/pushshift-reddit").
}

export interface DatasetCard {
  /** Stable identifier matching the DataSource type. */
  id: DataSource;
  /** Short label for chips / compact UI. */
  shortLabel: string;
  /** Label for the dropdown selector (includes key stats). */
  dropdownLabel: string;
  /** One-line description for the dropdown. */
  description: string;
  /** Source-of-truth facts — rendered as the dataset composition table. */
  facts: DatasetFact[];
  /** Short blurb shown above the subreddit list (explains scope). */
  subredditBlurb: string;
  /** Subreddits in this dataset, grouped by domain. Empty array = too many to enumerate (see blurb). */
  subredditGroups: SubredditGroup[];
}

// Helper: build a Reddit URL from a subreddit name (without r/ prefix).
const reddit = (name: string) => ({
  name: `r/${name}`,
  url: `https://reddit.com/r/${name}`,
});

// ── Curated subreddit knowledge base for the live scrapers (reddit_live + reddit_v2) ──
// Used by preprocessing (Call 8) to pick relevant subs for a topic.
const LIVE_SUBREDDIT_GROUPS: SubredditGroup[] = [
  {
    domain: "Finance & Money",
    subs: [
      "personalfinance",
      "povertyfinance",
      "debtfree",
      "leanfire",
      "fatFIRE",
      "studentloans",
      "antiwork",
      "almosthomeless",
      "breakingmom",
      "realestateinvesting",
    ].map(reddit),
  },
  {
    domain: "Work & Career",
    subs: [
      "jobs",
      "recruitinghell",
      "cscareerquestions",
      "workreform",
      "careerguidance",
      "whitecollar",
      "productivity",
      "selfhosted",
      "entrepreneur",
      "software",
      "smallbusiness",
      "freelance",
      "consulting",
    ].map(reddit),
  },
  {
    domain: "Relationships & Dating",
    subs: [
      "relationship_advice",
      "relationships",
      "amitheasshole",
      "breakups",
      "lonely",
      "dating",
      "datingoverthirty",
      "deadbedrooms",
    ].map(reddit),
  },
  {
    domain: "Parenting",
    subs: ["daddit", "beyondthebump", "parenting", "mommit"].map(reddit),
  },
  {
    domain: "Health & Psychology",
    subs: [
      "depression",
      "anxiety",
      "ADHD",
      "offmychest",
      "trueoffmychest",
      "therapy",
      "socialanxiety",
      "insomnia",
      "chronicpain",
      "chronicillness",
      "ehlersdanlos",
      "PCOS",
      "GERD",
      "Menopause",
      "Fibromyalgia",
      "diabetes",
      "diabetes_t2",
    ].map(reddit),
  },
  {
    domain: "Housing & Cost of Living",
    subs: ["FirstTimeHomeBuyer", "renting", "malelivingspace", "fuckcars"].map(reddit),
  },
  {
    domain: "Life Stage & Identity",
    subs: [
      "adulting",
      "quarterlifecrisis",
      "midlifecrisis",
      "ChildFree",
      "30PlusSkinCare",
      "malementalhealth",
    ].map(reddit),
  },
  {
    domain: "Caregiving",
    subs: ["AgingParents", "dementia", "caregiver"].map(reddit),
  },
  {
    domain: "Immigration & Legal",
    subs: ["immigration", "USCIS", "f1visa"].map(reddit),
  },
  {
    domain: "Consumer Frustration",
    subs: ["mildlyinfuriating", "assholedesign", "softwaregore", "talesfromtechsupport"].map(reddit),
  },
  {
    domain: "Entertainment",
    subs: [
      "patientgamers",
      "gaming",
      "gameideas",
      "gamedev",
      "pcgaming",
      "Steam",
      "indiegaming",
      "television",
      "cordcutters",
      "streamingwars",
      "moviesuggestions",
      "spotify",
      "vinyl",
      "WeAreTheMusicMakers",
      "suggestmeabook",
      "kindle",
      "Audiobooks",
    ].map(reddit),
  },
];

// Live KB count — referenced by the how-it-works page header.
const LIVE_KB_COUNT = LIVE_SUBREDDIT_GROUPS.reduce((acc, g) => acc + g.subs.length, 0);

// ── The cards ──
// One entry per DataSource value. TypeScript will error if a source is missing.

export const DATASET_CARDS: Record<DataSource, DatasetCard> = {
  // ─── Pushshift (historical, Jan 2018) — renamed from "arcticshift" ───
  pushshift: {
    id: "pushshift",
    shortLabel: "Pushshift",
    dropdownLabel: "Pushshift (Jan 2018, 11.3M posts)",
    description: "Historical Reddit via HuggingFace Parquet + DuckDB SQL",
    facts: [
      { label: "Source", value: "HuggingFace fddemarco/pushshift-reddit (Parquet)" },
      { label: "File", value: "RS_2018-01_00.parquet (only Jan 2018 shard in the dataset)" },
      { label: "Vintage", value: "January 2018" },
      { label: "Size", value: "11,263,400 submissions" },
      { label: "Subreddits", value: "241,466 distinct" },
      { label: "Query method", value: "DuckDB SQL on title, score >= 1, top 100 by score" },
      { label: "Comments", value: "Not included" },
      { label: "Cache", value: "data/hf_cache/ (Parquet, after first download)" },
    ],
    subredditBlurb:
      "All 241,466 subreddits active in January 2018 are queryable at runtime via DuckDB SQL. Too many to enumerate here — any subreddit name in the archive can be filtered on directly.",
    subredditGroups: [],
  },

  // ─── Linanqiu (local JSON, Feb 2016) ───
  linanqiu: {
    id: "linanqiu",
    shortLabel: "Linanqiu",
    dropdownLabel: "Linanqiu (Feb 2016, ~10K posts)",
    description: "10K posts from github.com/linanqiu/reddit-dataset",
    facts: [
      { label: "Source", value: "github.com/linanqiu/reddit-dataset (local JSON export)" },
      { label: "Vintage", value: "February 2016" },
      { label: "Size", value: "~10,170 posts" },
      { label: "Subreddits", value: "51 across 7 categories" },
      { label: "Query method", value: "In-memory keyword filter on title OR body, ups >= 1, top 100" },
      { label: "Comments", value: "Not included (titles synthesized where missing)" },
      { label: "Cache", value: "None — reloaded each run" },
    ],
    subredditBlurb:
      "All 51 subreddits in the dataset, grouped by the original category prefixes in the source CSV filenames.",
    subredditGroups: [
      {
        domain: "Entertainment",
        subs: ["anime", "comicbooks", "harrypotter", "movies", "music", "starwars"].map(reddit),
      },
      {
        domain: "Gaming",
        subs: ["dota2", "gaming", "leagueoflegends", "minecraft", "pokemon", "skyrim", "starcraft", "tf2"].map(reddit),
      },
      {
        domain: "Humor",
        subs: ["adviceanimals", "circlejerk", "facepalm", "funny", "imgoingtohellforthis", "jokes"].map(reddit),
      },
      {
        domain: "Learning",
        subs: ["askhistorians", "askscience", "explainlikeimfive", "science", "space", "todayilearned", "youshouldknow"].map(reddit),
      },
      {
        domain: "Lifestyle",
        subs: ["drunk", "food", "frugal", "guns", "lifehacks", "motorcycles", "progresspics", "sex"].map(reddit),
      },
      {
        domain: "News",
        subs: ["conservative", "conspiracy", "libertarian", "news", "offbeat", "politics", "truereddit", "worldnews"].map(reddit),
      },
      {
        domain: "Television",
        subs: ["breakingbad", "community", "doctorwho", "gameofthrones", "himym", "mylittlepony", "startrek", "thewalkingdead"].map(reddit),
      },
    ],
  },

  // ─── Sample default (3 subs) ───
  sample_default: {
    id: "sample_default",
    shortLabel: "Sample",
    dropdownLabel: "Sample (3 subs, Apr 2026)",
    description: "30 posts from r/antiwork, r/personalfinance, r/ADHD",
    facts: [
      { label: "Source", value: "data/smallsample/sample_posts.json" },
      { label: "Vintage", value: "April 2026" },
      { label: "Size", value: "30 posts" },
      { label: "Subreddits", value: "3 (r/antiwork, r/personalfinance, r/ADHD)" },
      { label: "Query method", value: "Whole file loaded (no filtering)" },
      { label: "Comments", value: "Not included" },
      { label: "Cache", value: "None — reloaded each run" },
    ],
    subredditBlurb: "All 3 subreddits represented in the sample.",
    subredditGroups: [
      {
        domain: "Subreddits",
        subs: ["antiwork", "personalfinance", "ADHD"].map(reddit),
      },
    ],
  },

  // ─── Sample gaming (4 subs, NOT 5 — prior UI was wrong) ───
  sample_gaming: {
    id: "sample_gaming",
    shortLabel: "Sample Gaming",
    dropdownLabel: "Sample Gaming (4 subs, Apr 2026)",
    description: "36 posts across 4 gaming subreddits (test dataset)",
    facts: [
      { label: "Source", value: "data/smallsample/gaming_test_20260416_105527.json" },
      { label: "Vintage", value: "April 2026" },
      { label: "Size", value: "36 posts" },
      { label: "Subreddits", value: "4 (r/gaming, r/indiegaming, r/patientgamers, r/pcgaming)" },
      { label: "Query method", value: "Whole file loaded (no filtering)" },
      { label: "Comments", value: "Not included" },
      { label: "Cache", value: "None — reloaded each run" },
    ],
    subredditBlurb: "All 4 subreddits represented in the gaming sample.",
    subredditGroups: [
      {
        domain: "Subreddits",
        subs: ["gaming", "indiegaming", "patientgamers", "pcgaming"].map(reddit),
      },
    ],
  },

  // ─── Reddit Live (real-time API) ───
  reddit_live: {
    id: "reddit_live",
    shortLabel: "Reddit Live v1",
    dropdownLabel: "Reddit Live API v1 (real-time scraping)",
    description: "Live Reddit API via OAuth (discontinued)",
    facts: [
      { label: "Source", value: "Reddit API (OAuth)" },
      { label: "Vintage", value: "Real-time" },
      { label: "Size", value: "Variable (per query, capped at 100)" },
      { label: "Subreddits", value: `Curated knowledge base (${LIVE_KB_COUNT} subs)` },
      { label: "Query method", value: "Top posts by subreddit, score >= 1" },
      { label: "Comments", value: "Top comments per post" },
      { label: "Cache", value: "First query cached to disk, reused for the same topic" },
    ],
    subredditBlurb:
      "Curated knowledge base used by the preprocessing step (Call 8). The LLM picks relevant subs from this list based on the user's topic.",
    subredditGroups: LIVE_SUBREDDIT_GROUPS,
  },

  // ─── Reddit v2 (old.reddit.com HTML scraper) ───
  reddit_v2: {
    id: "reddit_v2",
    shortLabel: "Reddit Live v2",
    dropdownLabel: "Reddit Live API v2 (real-time scraping)",
    description: "Scrape old.reddit.com HTML in real-time",
    facts: [
      { label: "Source", value: "old.reddit.com (HTML scraper)" },
      { label: "Vintage", value: "Real-time" },
      { label: "Size", value: "Variable (per query, capped at 100)" },
      { label: "Subreddits", value: `Curated knowledge base (${LIVE_KB_COUNT} subs)` },
      { label: "Query method", value: "Scrape HTML listing pages, parse posts" },
      { label: "Comments", value: "Top comments per post" },
      { label: "Cache", value: "None" },
    ],
    subredditBlurb:
      "Uses the same curated knowledge base as Reddit Live. The LLM picks relevant subs from this list based on the user's topic.",
    subredditGroups: LIVE_SUBREDDIT_GROUPS,
  },
};

// Convenience: live sources share the curated KB.
export const LIVE_KB_SUBREDDIT_COUNT = LIVE_KB_COUNT;
