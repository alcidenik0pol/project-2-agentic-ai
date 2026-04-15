"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import type { AnalysisPhase } from "@/lib/types";

interface ChatInterfaceProps {
  onSubmit: (query: string, mode: "test" | "live") => void;
  phase: AnalysisPhase;
  onCancel: () => void;
}

export function ChatInterface({ onSubmit, phase, onCancel }: ChatInterfaceProps) {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<"test" | "live">("live");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const isRunning = phase === "running" || phase === "submitting";

  // Clear query when transitioning to a ready state
  useEffect(() => {
    if (phase === "idle" || phase === "completed" || phase === "failed") {
      setQuery("");
    }
  }, [phase]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [query]);

  const handleSubmit = () => {
    if (!query.trim() || isRunning) return;
    onSubmit(query.trim(), mode);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="w-full max-w-[700px] mx-auto">
      <div className="relative">
        {/* Input row */}
        <div className="flex items-center gap-2">
          <textarea
            ref={textareaRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Enter an industry or niche to discover pain points and business ideas (e.g., 'gaming', 'remote work', 'fitness')..."
            disabled={isRunning}
            rows={1}
            className="flex-1 border border-input bg-background px-3 py-2.5 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring focus-visible:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50 resize-none rounded-md overflow-y-hidden"
          />
          <div className="flex items-center gap-2">
            {isRunning ? (
              <Button variant="destructive" onClick={onCancel} className="h-9 px-4">
                Cancel
              </Button>
            ) : (
              <Button
                onClick={handleSubmit}
                disabled={!query.trim()}
                className="h-9 px-4"
              >
                Analyze
              </Button>
            )}
            <label className="flex items-center gap-1.5 cursor-pointer group shrink-0">
              <input
                type="checkbox"
                checked={mode === "test"}
                onChange={(e) => setMode(e.target.checked ? "test" : "live")}
                className="w-3.5 h-3.5 accent-muted-foreground"
              />
              <span
                className="text-xs text-muted-foreground group-hover:text-foreground transition-colors"
                title="Run on static data. For testing purposes only."
              >
                Test Mode
              </span>
            </label>
          </div>
        </div>

        {/* Attribution */}
        <div className="flex justify-end mt-1">
          <span className="text-[10px] text-muted-foreground/50">
            Powered by Reddit
          </span>
        </div>
      </div>
    </div>
  );
}
