"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import type { AnalysisPhase } from "@/lib/types";

interface ChatInterfaceProps {
  onSubmit: (query: string, mode: "test" | "live") => void;
  phase: AnalysisPhase;
  onCancel: () => void;
}

function ModeToggle({ mode, setMode, isRunning }: { mode: "test" | "live"; setMode: (m: "test" | "live") => void; isRunning: boolean }) {
  const isLive = mode === "live";

  return (
    <button
      onClick={() => !isRunning && setMode(isLive ? "test" : "live")}
      disabled={isRunning}
      className={`
        flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium
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

export function ChatInterface({ onSubmit, phase, onCancel }: ChatInterfaceProps) {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<"test" | "live">("live");
  const inputRef = useRef<HTMLInputElement>(null);

  const isRunning = phase === "running" || phase === "submitting";

  // Clear query when transitioning to a ready state
  useEffect(() => {
    if (phase === "idle" || phase === "completed" || phase === "failed") {
      setQuery("");
    }
  }, [phase]);

  const handleSubmit = () => {
    if (!query.trim() || isRunning) return;
    onSubmit(query.trim(), mode);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="w-full max-w-[700px] mx-auto">
      <div className="bg-card border border-white/10 rounded-lg p-[12px_16px]">
        {/* Main controls row: Input + Button only */}
        <div className="flex items-center gap-3">
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Drop an industry. We'll find the gold in Reddit users' complaints."
            disabled={isRunning}
            className="flex-1 h-12 border border-input bg-background px-3 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring focus-visible:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50 rounded-md"
          />
          {isRunning ? (
            <Button variant="destructive" onClick={onCancel} className="h-12 px-4">
              Stop panning
            </Button>
          ) : (
            <Button
              onClick={handleSubmit}
              disabled={!query.trim()}
              className="h-12 px-4"
            >
              Pan it
            </Button>
          )}
        </div>

        {/* Test mode toggle - right aligned */}
        <div className="flex justify-end mt-2">
          <ModeToggle mode={mode} setMode={setMode} isRunning={isRunning} />
        </div>

        {/* Panned from Reddit - right aligned, larger */}
        <div className="flex justify-end items-center gap-1.5 mt-2">
          <span className="text-[13px] text-muted-foreground/60">
            Panned from Reddit
          </span>
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor" className="opacity-60 shrink-0"><path d="M12 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0zm5.01 4.744c.688 0 1.25.561 1.25 1.249a1.25 1.25 0 0 1-2.498.056l-2.597-.547-.8 3.747c1.732.07 3.303.682 4.332 1.598a1.978 1.978 0 0 1 1.376-.588h.027a1.978 1.978 0 0 1 1.978 1.977 1.978 1.978 0 0 1-1.96 1.99c-.033.736-.376 1.416-.933 1.944-.58.55-1.373.966-2.296 1.216a9.38 9.38 0 0 1-2.52.336 9.37 9.37 0 0 1-2.52-.336c-.924-.25-1.717-.666-2.296-1.216a3.07 3.07 0 0 1-.934-1.944A1.978 1.978 0 0 1 3.23 12.23a1.978 1.978 0 0 1 1.978-1.977h.027c.527 0 1.01.212 1.376.588 1.03-.916 2.6-1.528 4.332-1.598l.878-4.108a.397.397 0 0 1 .12-.2.396.396 0 0 1 .294-.084l2.837.596a1.245 1.245 0 0 1 1.048-.573zM9.25 12.13a1.25 1.25 0 0 0-1.25 1.25 1.25 1.25 0 0 0 1.25 1.25 1.25 1.25 0 0 0 1.25-1.25 1.25 1.25 0 0 0-1.25-1.25zm5.5 0a1.25 1.25 0 0 0-1.25 1.25 1.25 1.25 0 0 0 1.25 1.25 1.25 1.25 0 0 0 1.25-1.25 1.25 1.25 0 0 0-1.25-1.25zm-5.862 3.915a.397.397 0 0 0-.12.584c.708.817 2.046 1.14 3.232 1.14s2.524-.323 3.232-1.14a.397.397 0 0 0-.12-.584.397.397 0 0 0-.546.084c-.47.545-1.478.903-2.566.903-1.088 0-2.096-.358-2.566-.903a.397.397 0 0 0-.546-.084z"/></svg>
        </div>
      </div>
    </div>
  );
}
