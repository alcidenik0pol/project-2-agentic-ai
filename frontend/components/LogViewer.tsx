"use client";

import { useEffect, useRef, useState } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import type { LogEntry } from "@/lib/types";
import { stripAnsiCodes } from "@/lib/utils";

interface LogViewerProps {
  logs: LogEntry[];
}

const LEVEL_STYLES: Record<string, string> = {
  INFO: "text-muted-foreground",
  WARNING: "text-yellow-400",
  ERROR: "text-red-400",
};

function formatTimestamp(ts: number): string {
  const d = new Date(ts);
  return d.toLocaleTimeString("en-US", { hour12: false });
}

export function LogViewer({ logs }: LogViewerProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [filterLevel, setFilterLevel] = useState<string>("all");

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      const el = scrollRef.current;
      el.scrollTop = el.scrollHeight;
    }
  }, [logs, autoScroll]);

  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    setAutoScroll(scrollHeight - scrollTop - clientHeight < 50);
  };

  const filteredLogs = filterLevel === "all"
    ? logs
    : logs.filter((l) => l.level === filterLevel);

  const copyAll = () => {
    const text = filteredLogs
      .map((l) => `[${formatTimestamp(l.timestamp)}] [${l.level}] ${l.agent_name ? `[${l.agent_name}] ` : ""}${stripAnsiCodes(l.message)}`)
      .join("\n");
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          Logs ({logs.length})
        </span>
        <div className="flex items-center gap-2">
          {["all", "INFO", "WARNING", "ERROR"].map((level) => (
            <button
              key={level}
              onClick={() => setFilterLevel(level)}
              className={`px-2 py-0.5 text-[10px] font-medium transition-colors ${
                filterLevel === level
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
              }`}
            >
              {level}
            </button>
          ))}
          <Button variant="ghost" size="sm" onClick={copyAll} className="h-6 text-[10px]">
            Copy
          </Button>
        </div>
      </div>
      <ScrollArea className="h-[250px]">
        <div
          ref={scrollRef}
          onScroll={handleScroll}
          className="font-mono text-xs space-y-0.5 overflow-y-auto h-[250px]"
        >
          {filteredLogs.length === 0 ? (
            <div className="text-muted-foreground text-center py-8">
              Waiting for logs...
            </div>
          ) : (
            filteredLogs.map((log) => (
              <div key={log.id} className="flex gap-2 leading-relaxed break-words">
                <span className="text-muted-foreground flex-shrink-0">
                  {formatTimestamp(log.timestamp)}
                </span>
                <span className={`flex-shrink-0 w-16 ${LEVEL_STYLES[log.level] || ""}`}>
                  [{log.level}]
                </span>
                {log.agent_name && (
                  <span className="flex-shrink-0 w-24 text-primary font-medium">
                    [{log.agent_name}]
                  </span>
                )}
                <span className="break-words">{stripAnsiCodes(log.message)}</span>
              </div>
            ))
          )}
        </div>
      </ScrollArea>
      {!autoScroll && (
        <div className="flex justify-center mt-1">
          <Button
            variant="ghost"
            size="sm"
            className="text-[10px] h-5"
            onClick={() => {
              setAutoScroll(true);
              if (scrollRef.current) {
                scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
              }
            }}
          >
            Auto-scroll paused - click to resume
          </Button>
        </div>
      )}
    </div>
  );
}
