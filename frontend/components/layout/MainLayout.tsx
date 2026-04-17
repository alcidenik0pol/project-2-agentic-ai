"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Navbar } from "@/components/Navbar";
import { PipelineVideoPlayer } from "@/components/PipelineVideoPlayer";
import PIPELINE_VIDEOS from "@/config/videos.json";
import { useGlobalWebSocket } from "@/hooks/useGlobalWebSocket";
import { useAnalysis } from "@/contexts/AnalysisContext";
import type { AnalysisPhase } from "@/lib/types";

const NAV_LINKS = [
  { href: "/", label: "Home" },
  { href: "/rate-limit", label: "Rate Limit" },
  { href: "/debug", label: "Debug" },
  { href: "/how-it-works", label: "How it Works" },
];

export function MainLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { phase: analysisPhase } = useAnalysis();
  const { phase: wsPhase } = useGlobalWebSocket();

  const phase: AnalysisPhase =
    wsPhase === "running" ? "running" :
    wsPhase === "completed" ? "completed" :
    wsPhase === "failed" ? "failed" :
    analysisPhase;

  const showVideo = phase === "running" && PIPELINE_VIDEOS.length > 0;

  return (
    <div className="min-h-screen flex flex-col">
      {/* Mobile nav - horizontal scroll */}
      <div className="sm:hidden border-b border-border">
        <nav className="flex items-center gap-1 px-2 py-2 overflow-x-auto">
          <Link href="/" className="text-xs font-bold tracking-tight mr-3 flex-shrink-0">
            RBI
          </Link>
          {NAV_LINKS.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`px-2 py-1 text-[10px] font-medium flex-shrink-0 transition-colors ${
                  isActive
                    ? "text-foreground bg-secondary"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
      {/* Desktop navbar */}
      <div className="hidden sm:block">
        <Navbar />
      </div>
      {/* Video player persists across page navigations */}
      <div
        style={{
          display: "grid",
          gridTemplateRows: showVideo ? "1fr" : "0fr",
          transition: "grid-template-rows 0.5s ease-out",
        }}
      >
        <div className="overflow-hidden">
          <div className="flex justify-center px-4 pt-4">
            <PipelineVideoPlayer videoIds={PIPELINE_VIDEOS} />
          </div>
        </div>
      </div>
      <main className="flex-1">
        {children}
      </main>
    </div>
  );
}
