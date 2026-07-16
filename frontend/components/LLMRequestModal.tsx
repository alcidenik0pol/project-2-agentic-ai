"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { X, Copy } from "lucide-react";
import type { LLMCallData } from "@/lib/types";

interface LLMRequestModalProps {
  data: LLMCallData;
  onClose: () => void;
}

export function LLMRequestModal({ data, onClose }: LLMRequestModalProps) {
  // Escape to close + lock body scroll while open
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKey);

    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      window.removeEventListener("keydown", handleKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [onClose]);

  const copyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(data.request, null, 2));
  };

  const s = data.response_summary;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-3xl max-h-[80vh] flex flex-col bg-card border border-border rounded-md shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-border">
          <div className="flex-1 min-w-0">
            <div className="text-sm font-mono font-medium truncate">
              {data.provider} / {data.model}
            </div>
            <div className="text-[11px] text-muted-foreground uppercase tracking-wider">
              {data.method}
            </div>
          </div>
          <Button variant="outline" size="sm" onClick={copyJson} className="h-7 text-xs">
            <Copy className="w-3.5 h-3.5 mr-1.5" />
            Copy JSON
          </Button>
          <Button variant="ghost" size="sm" onClick={onClose} className="h-7 w-7 p-0">
            <X className="w-4 h-4" />
          </Button>
        </div>

        {/* Summary bar */}
        <div className="flex flex-wrap gap-x-4 gap-y-1 px-4 py-2 border-b border-border text-[11px] font-mono">
          <span>
            <span className="text-muted-foreground">elapsed:</span>{" "}
            <span className="text-foreground">{s.elapsed_seconds?.toFixed(2)}s</span>
          </span>
          {s.finish_reason && (
            <span>
              <span className="text-muted-foreground">finish:</span>{" "}
              <span className="text-foreground">{s.finish_reason}</span>
            </span>
          )}
          <span>
            <span className="text-muted-foreground">content:</span>{" "}
            <span className="text-foreground">{s.content_chars} chars</span>
          </span>
          {typeof s.tool_call_count === "number" && (
            <span>
              <span className="text-muted-foreground">tool_calls:</span>{" "}
              <span className="text-foreground">
                {s.tool_call_count}
                {s.tool_call_names && s.tool_call_names.length > 0 && (
                  <span className="text-muted-foreground">
                    {" "}({s.tool_call_names.join(", ")})
                  </span>
                )}
              </span>
            </span>
          )}
        </div>

        {/* Body: pretty-printed request JSON */}
        <div className="flex-1 overflow-auto p-4">
          <pre className="text-[11px] font-mono leading-relaxed whitespace-pre-wrap break-all">
            {JSON.stringify(data.request, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
}
