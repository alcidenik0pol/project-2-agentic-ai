"use client";

import { useState, useRef } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Navbar } from "@/components/Navbar";
import { PipelineVideoPlayer } from "@/components/PipelineVideoPlayer";
import PIPELINE_VIDEOS from "@/config/videos.json";
import { useGlobalWebSocket } from "@/hooks/useGlobalWebSocket";
import { useAnalysis } from "@/contexts/AnalysisContext";
import { NAV_LINKS } from "@/lib/nav-links";
import type { AnalysisPhase } from "@/lib/types";

export function MainLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const { phase: analysisPhase } = useAnalysis();
  const { phase: wsPhase, runId } = useGlobalWebSocket();

  // Change the video key when a NEW run starts or when resetting to idle (nuke).
  // Resetting to "idle" forces a remount which destroys the old player and stops the video.
  const videoKeyRef = useRef<string>("idle");
  if (runId) {
    videoKeyRef.current = runId;
  } else {
    videoKeyRef.current = "idle";
  }

  const phase: AnalysisPhase =
    wsPhase === "running" ? "running" :
    wsPhase === "completed" ? "completed" :
    wsPhase === "failed" ? "failed" :
    analysisPhase;

  const showVideo = phase === "running" && PIPELINE_VIDEOS.length > 0;

  // Close menu on navigation
  const handleNavClick = () => setMenuOpen(false);

  return (
    <div className="min-h-screen flex flex-col">
      {/* Mobile nav - burger menu */}
      <div className="sm:hidden border-b border-border">
        <div className="flex items-center justify-between px-4 py-2">
          <Link href="/" className="text-sm font-bold tracking-tight" onClick={handleNavClick}>
            Based Instinct
          </Link>
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="p-2 -mr-2 text-muted-foreground hover:text-foreground"
            aria-label="Toggle menu"
          >
            {/* Burger / X icon */}
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
              {menuOpen ? (
                <>
                  <line x1="4" y1="4" x2="16" y2="16" />
                  <line x1="16" y1="4" x2="4" y2="16" />
                </>
              ) : (
                <>
                  <line x1="3" y1="5" x2="17" y2="5" />
                  <line x1="3" y1="10" x2="17" y2="10" />
                  <line x1="3" y1="15" x2="17" y2="15" />
                </>
              )}
            </svg>
          </button>
        </div>
        {/* Dropdown menu */}
        {menuOpen && (
          <nav className="flex flex-col border-t border-border px-4 py-2">
            {NAV_LINKS.map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={handleNavClick}
                  className={`px-3 py-2.5 text-sm font-medium transition-colors ${
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
        )}
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
            <PipelineVideoPlayer key={videoKeyRef.current} videoIds={PIPELINE_VIDEOS} active={showVideo} />
          </div>
        </div>
      </div>
      <main className="flex-1">
        {children}
      </main>
    </div>
  );
}
