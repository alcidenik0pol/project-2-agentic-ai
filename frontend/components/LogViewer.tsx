"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { LLMRequestModal } from "@/components/LLMRequestModal";
import type { LLMCallData, LogEntry } from "@/lib/types";
import { stripAnsiCodes } from "@/lib/utils";

interface LogViewerProps {
  logs: LogEntry[];
}

const LEVEL_STYLES: Record<string, string> = {
  INFO: "text-muted-foreground",
  WARNING: "text-yellow-400",
  ERROR: "text-red-400",
};

const LEVELS = ["INFO", "WARNING", "ERROR"] as const;
const LEVEL_SHORT: Record<string, string> = {
  INFO: "INFO",
  WARNING: "WARN",
  ERROR: "ERR",
};

function formatTimestamp(ts: number): string {
  const d = new Date(ts);
  return d.toLocaleTimeString("en-US", { hour12: false });
}

export function LogViewer({ logs }: LogViewerProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [enabledLevels, setEnabledLevels] = useState<Set<string>>(
    new Set(LEVELS)
  );
  const [modalData, setModalData] = useState<LLMCallData | null>(null);

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

  // Per-level counts (over ALL logs, not the filtered view)
  const counts = useMemo(() => {
    const c: Record<string, number> = { INFO: 0, WARNING: 0, ERROR: 0 };
    for (const l of logs) {
      if (c[l.level] !== undefined) c[l.level]++;
    }
    return c;
  }, [logs]);

  const allOn = LEVELS.every((l) => enabledLevels.has(l));

  const toggleLevel = (level: string) => {
    setEnabledLevels((prev) => {
      const next = new Set(prev);
      if (next.has(level)) next.delete(level);
      else next.add(level);
      return next;
    });
  };

  const resetAll = () => setEnabledLevels(new Set(LEVELS));

  const filteredLogs = useMemo(
    () => logs.filter((l) => enabledLevels.has(l.level)),
    [logs, enabledLevels]
  );

  const copyAll = () => {
    const text = filteredLogs
      .map((l) => {
        const llmTag = l.llmCall ? `[LLM: ${l.llmCall.method}] ` : "";
        return `[${formatTimestamp(l.timestamp)}] [${l.level}] ${
          l.agent_name ? `[${l.agent_name}] ` : ""
        }${llmTag}${stripAnsiCodes(l.message)}`;
      })
      .join("\n");
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-1.5 flex-wrap">
          <button
            onClick={resetAll}
            className={`px-2 py-0.5 text-[10px] font-medium transition-colors border ${
              allOn
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-secondary/50 text-muted-foreground border-border hover:bg-secondary"
            }`}
          >
            ALL ({logs.length})
          </button>
          {LEVELS.map((level) => {
            const active = enabledLevels.has(level);
            const hasCount = counts[level] > 0;
            return (
              <button
                key={level}
                onClick={() => toggleLevel(level)}
                className={`px-2 py-0.5 text-[10px] font-medium transition-colors border ${
                  active && hasCount
                    ? level === "ERROR"
                      ? "bg-red-500/20 text-red-400 border-red-500/40"
                      : level === "WARNING"
                      ? "bg-yellow-500/20 text-yellow-400 border-yellow-500/40"
                      : "bg-blue-500/20 text-blue-400 border-blue-500/40"
                    : "bg-secondary/30 text-muted-foreground/50 border-border hover:bg-secondary/50"
                }`}
              >
                {LEVEL_SHORT[level]} ({counts[level]})
              </button>
            );
          })}
        </div>
        <Button variant="ghost" size="sm" onClick={copyAll} className="h-6 text-[10px]">
          Copy full log
        </Button>
      </div>
      <ScrollArea className="h-[250px]">
        <div
          ref={scrollRef}
          onScroll={handleScroll}
          className="font-mono text-xs space-y-0.5 overflow-y-auto overscroll-contain h-[250px]"
        >
          {filteredLogs.length === 0 ? (
            <div className="text-muted-foreground text-center py-8">
              {logs.length === 0
                ? "Waiting for logs..."
                : "No entries match the current filter."}
            </div>
          ) : (
            filteredLogs.map((log) =>
              log.llmCall ? (
                <button
                  key={log.id}
                  onClick={() => setModalData(log.llmCall!)}
                  className="w-full flex gap-2 leading-relaxed break-words text-left hover:bg-accent/30 px-1 -mx-1 cursor-pointer"
                >
                  <span className="text-muted-foreground flex-shrink-0">
                    {formatTimestamp(log.timestamp)}
                  </span>
                  <span className="flex-shrink-0 w-16 text-purple-400 font-medium">
                    [LLM]
                  </span>
                  <span className="flex-shrink-0 text-purple-300/80">{`{ }`}</span>
                  <span className="break-words text-purple-200">
                    {log.llmCall.provider}/{log.llmCall.model}{" "}
                    {log.llmCall.method}{" "}
                    <span className="text-muted-foreground">
                      ({log.llmCall.response_summary.elapsed_seconds?.toFixed(2)}s
                      {typeof log.llmCall.response_summary.tool_call_count === "number"
                        ? `, ${log.llmCall.response_summary.tool_call_count} tool_calls`
                        : ""})
                    </span>
                  </span>
                </button>
              ) : (
                <div key={log.id} className="flex gap-2 leading-relaxed break-words">
                  <span className="text-muted-foreground flex-shrink-0">
                    {formatTimestamp(log.timestamp)}
                  </span>
                  <span className={`flex-shrink-0 w-16 ${LEVEL_STYLES[log.level] || ""}`}>
                    [{LEVEL_SHORT[log.level]}]
                  </span>
                  {log.agent_name && (
                    <span className="flex-shrink-0 w-24 text-primary font-medium truncate">
                      [{log.agent_name}]
                    </span>
                  )}
                  <span className="break-words">{stripAnsiCodes(log.message)}</span>
                </div>
              )
            )
          )}
          {!autoScroll && filteredLogs.length > 0 && (
            <button
              type="button"
              onClick={() => {
                setAutoScroll(true);
                if (scrollRef.current) {
                  scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
                }
              }}
              className="sticky bottom-0 left-0 right-0 w-full flex justify-center py-1 bg-card border-t border-border text-[10px] text-muted-foreground hover:bg-secondary/60 transition-colors cursor-pointer"
            >
              Auto-scroll paused - click to resume
            </button>
          )}
        </div>
      </ScrollArea>
      {modalData && (
        <LLMRequestModal data={modalData} onClose={() => setModalData(null)} />
      )}
    </div>
  );
}
