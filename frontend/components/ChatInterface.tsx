"use client";

import { useState, useRef, useEffect } from "react";
import Image from "next/image";
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
      <p className="text-sm text-foreground mb-2">
        Drop an industry. We'll find the gold in Reddit users' complaints.
      </p>
      <div className="bg-card border border-white/10 rounded-lg p-[12px_16px]">
        {/* Main controls row */}
        <div className="flex items-center gap-3">
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="e.g. gaming, remote work, fitness..."
            disabled={isRunning}
            className="flex-1 h-12 border border-input bg-background px-3 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring focus-visible:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50 rounded-md"
          />
          <div className="flex items-center gap-2">
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
            <label className="flex items-center gap-1.5 cursor-pointer group shrink-0 h-12">
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
        {/* Panned from Reddit */}
        <div className="flex justify-end items-center gap-1.5">
          <span className="text-[11px] text-muted-foreground/40">
            Panned from
          </span>
          <Image
            src="/reddit-svgrepo-com.svg"
            alt="Reddit"
            width={14}
            height={14}
            className="opacity-40"
          />
        </div>
      </div>
    </div>
  );
}
