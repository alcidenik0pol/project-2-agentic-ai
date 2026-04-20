"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import type { AnalysisPhase } from "@/lib/types";

interface ChatInterfaceProps {
  onSubmit: (query: string, mode: "test" | "live") => void;
  phase: AnalysisPhase;
  onCancel: () => void;
  onReset?: () => void;
}

function ModeToggle({ mode, setMode, isRunning }: { mode: "test" | "live"; setMode: (m: "test" | "live") => void; isRunning: boolean }) {
  const isLive = mode === "live";

  const tooltipText = isLive
    ? "On = Scrape hot posts from Reddit."
    : "Off =For testing purposes only. Data from a static extract of 30 Reddit posts from r/antiwork, r/personalfinance, and r/ADHD (fetched April 7, 2026)";

  return (
    <button
      onClick={() => !isRunning && setMode(isLive ? "test" : "live")}
      disabled={isRunning}
      title={tooltipText}
      className={`
        flex items-center gap-2 px-2 py-1 sm:px-3 sm:py-1.5 rounded text-[11px] sm:text-xs font-medium
        transition-all duration-200 ease-in-out
        ${isLive
          ? "bg-green-500/20 text-green-400 border border-green-500/30"
          : "bg-muted/40 text-muted-foreground border border-border"
        }
        ${isRunning ? "opacity-50 cursor-not-allowed" : "hover:opacity-80 cursor-pointer"}
      `}
    >
      <span className={`
        w-2 h-2 rounded-full transition-colors
        ${isLive ? "bg-green-400" : "bg-muted-foreground"}
      `} />
      {isLive ? "Scraping on" : "Static data"}
    </button>
  );
}

const MIN_QUERY_LENGTH = 3;

const DEFAULT_PLACEHOLDER = "Drop a niche. We'll interrogate the crowd.";
const DEFAULT_WEIGHT = 0.2; // 20% chance per cycle

const TOPIC_HINTS = [
  // Serious / High-signal
  "artificial intelligence",
  "fast food",
  "student loans",
  "remote work",
  "insurance",
  "electric vehicles",
  "crypto exchanges",
  "dating apps",
  "healthcare billing",
  "airlines",
  "landlords",
  // Funny / Uncommon
  "pigeons",
  "escape rooms",
  "astrology",
  "hot yoga",
  "sourdough bread",
  "renaissance faires",
  "thrift stores",
  "IKEA",
  "golf",
  "passive income gurus",
  "coworking spaces",
  "beard grooming",
  "cat owners",
  "CrossFit",
  "matcha",
  // Wildcard / Unexpectedly Juicy
  "funerals",
  "weddings",
  "dentists",
  "gym bros",
  "LinkedIn",
  "flight attendants",
];

const TYPE_SPEED = 60;
const DELETE_SPEED = 40;
const PAUSE_AFTER_TYPE = 2000;
const PAUSE_BEFORE_TYPE = 300;

export function ChatInterface({ onSubmit, phase, onCancel, onReset }: ChatInterfaceProps) {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<"test" | "live">("live");
  const [showMinLengthError, setShowMinLengthError] = useState(false);
  const [placeholder, setPlaceholder] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const currentPhraseRef = useRef(DEFAULT_PLACEHOLDER);
  const charIndexRef = useRef(0);
  const isDeletingRef = useRef(false);

  const isRunning = phase === "running" || phase === "submitting";

  /** Pick next phrase: DEFAULT_PLACEHOLDER with DEFAULT_WEIGHT, random TOPIC_HINT otherwise. Never repeats. */
  const pickNext = (current: string): string => {
    const candidates = [DEFAULT_PLACEHOLDER, ...TOPIC_HINTS].filter(p => p !== current);
    if (Math.random() < DEFAULT_WEIGHT && DEFAULT_PLACEHOLDER !== current) return DEFAULT_PLACEHOLDER;
    return candidates[Math.floor(Math.random() * candidates.length)];
  };

  // Typing animation for placeholder
  useEffect(() => {
    // Don't animate while user has text or input is disabled
    if (query.length > 0 || isRunning) return;

    const animate = () => {
      const currentPhrase = currentPhraseRef.current;

      if (!isDeletingRef.current) {
        // Typing forward
        charIndexRef.current += 1;
        setPlaceholder(currentPhrase.slice(0, charIndexRef.current));

        if (charIndexRef.current === currentPhrase.length) {
          // Finished typing — pause, then start deleting
          isDeletingRef.current = true;
          timeoutRef.current = setTimeout(animate, PAUSE_AFTER_TYPE);
          return;
        }
        timeoutRef.current = setTimeout(animate, TYPE_SPEED);
      } else {
        // Deleting
        charIndexRef.current -= 1;
        setPlaceholder(currentPhrase.slice(0, charIndexRef.current));

        if (charIndexRef.current === 0) {
          // Finished deleting — pick next phrase
          isDeletingRef.current = false;
          currentPhraseRef.current = pickNext(currentPhraseRef.current);
          timeoutRef.current = setTimeout(animate, PAUSE_BEFORE_TYPE);
          return;
        }
        timeoutRef.current = setTimeout(animate, DELETE_SPEED);
      }
    };

    timeoutRef.current = setTimeout(animate, TYPE_SPEED);

    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [query, isRunning]);

  // Clear query when transitioning to a ready state
  useEffect(() => {
    if (phase === "idle" || phase === "completed" || phase === "failed") {
      setQuery("");
      setShowMinLengthError(false);
    }
  }, [phase]);

  const handleSubmit = () => {
    const trimmed = query.trim();
    if (!trimmed || isRunning) return;
    if (trimmed.length < MIN_QUERY_LENGTH) {
      setShowMinLengthError(true);
      return;
    }
    setShowMinLengthError(false);
    onSubmit(trimmed, mode);
  };

  const handleChange = (value: string) => {
    setQuery(value);
    if (value.trim().length >= MIN_QUERY_LENGTH) {
      setShowMinLengthError(false);
    }
  };

  const isSubmittable = query.trim().length >= MIN_QUERY_LENGTH;

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="w-full max-w-[700px] mx-auto">
      <div className="bg-card border border-white/10 rounded-lg p-[12px_16px]">
        {/* Input area */}
        <div className="flex flex-col sm:flex-row sm:items-start gap-2 sm:gap-3">
          <div className="flex-1 flex flex-col">
            <div className="flex items-center gap-2 sm:gap-3">
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => handleChange(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={placeholder}
                disabled={isRunning}
                className={`flex-1 h-10 sm:h-12 border bg-background px-3 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring focus-visible:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50 rounded-md ${
                  showMinLengthError ? "border-red-500/60" : "border-input"
                }`}
              />
              {/* Submit button - beside input on desktop, beside input on mobile too */}
              {isRunning ? (
                <button
                  disabled
                  className="h-10 sm:h-12 px-4 sm:px-5 shrink-0 text-sm font-semibold btn-investigating"
                >
                  Interrogating...
                </button>
              ) : (
                <button
                  onClick={handleSubmit}
                  disabled={!isSubmittable}
                  className="h-10 sm:h-12 px-4 sm:px-5 shrink-0 text-sm font-semibold btn-investigate-idle disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Investigate
                </button>
              )}
            </div>
            {showMinLengthError && (
              <p className="text-xs text-red-400 mt-1">
                Enter at least {MIN_QUERY_LENGTH} characters to search.
              </p>
            )}
            {/* Toggle + Reset - aligned with input */}
            <div className="flex items-center mt-2 gap-2">
              <ModeToggle mode={mode} setMode={setMode} isRunning={isRunning} />
              {onReset && (
                <button
                  onClick={onReset}
                  disabled={isRunning}
                  title="Reset analysis state"
                  className={`
                    flex items-center gap-2 px-2 py-1 sm:px-3 sm:py-1.5 rounded text-[11px] sm:text-xs font-medium
                    transition-all duration-200 ease-in-out
                    bg-orange-500/20 text-orange-400 border border-orange-500/30
                    ${isRunning ? "opacity-50 cursor-not-allowed" : "hover:opacity-80 cursor-pointer"}
                  `}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M11.83 2a9 9 0 0 0-4.61 1.23"/>
                    <path d="M2 12a10 10 0 0 0 5.86 9.1c.7.3 1.1.9.9 1.6l-.5 1.8 2.5-2a9.8 9.8 0 0 0 2.24 0l2.5 2-.5-1.8c-.2-.7.2-1.3.9-1.6A10 10 0 0 0 2 12"/>
                    <circle cx="12" cy="11" r="2"/>
                    <path d="M12 9v-1"/>
                    <path d="M15 13h1"/>
                    <path d="M8 13h1"/>
                    <path d="M12 14v1"/>
                  </svg>
                  Nuke
                </button>
              )}
            </div>
            {/* Powered by - aligned to input width */}
            <div className="flex justify-end items-center gap-1.5 mt-2">
              <span className="text-[11px] sm:text-[13px] text-muted-foreground/60">
                Powered by Reddit
              </span>
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor" className="opacity-60 shrink-0"><path d="M12 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0zm5.01 4.744c.688 0 1.25.561 1.25 1.249a1.25 1.25 0 0 1-2.498.056l-2.597-.547-.8 3.747c1.732.07 3.303.682 4.332 1.598a1.978 1.978 0 0 1 1.376-.588h.027a1.978 1.978 0 0 1 1.978 1.977 1.978 1.978 0 0 1-1.96 1.99c-.033.736-.376 1.416-.933 1.944-.58.55-1.373.966-2.296 1.216a9.38 9.38 0 0 1-2.52.336 9.37 9.37 0 0 1-2.52-.336c-.924-.25-1.717-.666-2.296-1.216a3.07 3.07 0 0 1-.934-1.944A1.978 1.978 0 0 1 3.23 12.23a1.978 1.978 0 0 1 1.978-1.977h.027c.527 0 1.01.212 1.376.588 1.03-.916 2.6-1.528 4.332-1.598l.878-4.108a.397.397 0 0 1 .12-.2.396.396 0 0 1 .294-.084l2.837.596a1.245 1.245 0 0 1 1.048-.573zM9.25 12.13a1.25 1.25 0 0 0-1.25 1.25 1.25 1.25 0 0 0 1.25 1.25 1.25 1.25 0 0 0 1.25-1.25 1.25 1.25 0 0 0-1.25-1.25zm5.5 0a1.25 1.25 0 0 0-1.25 1.25 1.25 1.25 0 0 0 1.25 1.25 1.25 1.25 0 0 0 1.25-1.25 1.25 1.25 0 0 0-1.25-1.25zm-5.862 3.915a.397.397 0 0 0-.12.584c.708.817 2.046 1.14 3.232 1.14s2.524-.323 3.232-1.14a.397.397 0 0 0-.12-.584.397.397 0 0 0-.546.084c-.47.545-1.478.903-2.566.903-1.088 0-2.096-.358-2.566-.903a.397.397 0 0 0-.546-.084z"/></svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
