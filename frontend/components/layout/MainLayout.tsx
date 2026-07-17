"use client";

import { useState, useRef } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Navbar } from "@/components/Navbar";
import { PipelineVideoPlayer } from "@/components/PipelineVideoPlayer";
import PIPELINE_VIDEOS from "@/config/videos.json";
import { useGlobalWebSocket } from "@/hooks/useGlobalWebSocket";
import { useAnalysis } from "@/contexts/AnalysisContext";
import { AlertTriangle, X } from "lucide-react";
import { NAV_LINKS } from "@/lib/nav-links";
import type { AnalysisPhase } from "@/lib/types";

export function MainLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const { phase: analysisPhase, dataSource, setDataSource, videoEnabled } = useAnalysis();
  const { phase: wsPhase, runId } = useGlobalWebSocket();

  // Show the "discontinued" banner only for v1 — the legacy OAuth JSON API is
  // dead (403/410 since Reddit's May 2026 policy change). v2 (old.reddit HTML
  // scraper) is the replacement and must NOT show this banner.
  const showBanner = dataSource === "reddit_live" && !bannerDismissed;

  // Change the video key when a NEW run starts or when resetting to idle.
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
            Reddit Idea Miner
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
              const isRedditApiLink = link.href === "/rate-limit";
              const isDisabled = isRedditApiLink && dataSource !== "reddit_live" && dataSource !== "reddit_v2";

              if (isDisabled) {
                return (
                  <span
                    key={link.href}
                    className="px-3 py-2.5 text-sm font-medium text-muted-foreground/40 cursor-not-allowed"
                  >
                    {link.label}
                  </span>
                );
              }

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
      {/* Always reserve banner space to prevent layout shift */}
      <div className="min-h-[44px] sm:min-h-[52px]">
        {showBanner && (
          <div className="bg-amber-900/30 border-b border-amber-700/40 px-3 py-2 sm:px-4 sm:py-3">
            <div className="flex items-start gap-3 max-w-4xl mx-auto">
              <AlertTriangle className="h-4 w-4 text-amber-400 mt-0.5 shrink-0" />
              <p className="text-xs sm:text-sm text-amber-200 flex-1">
                <strong className="text-amber-100">Reddit Live API v1 is discontinued</strong>{" "}
                following Reddit&apos;s{" "}
                <a
                  href="https://www.reddit.com/r/modnews/comments/1tq9vxo/protecting_communities_from_scrapers_and_platform/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline text-amber-300 hover:text-amber-200"
                >
                  API policy change
                </a>{" "}
                (May 29, 2026).{" "}
                <button
                  onClick={() => setDataSource("reddit_v2")}
                  className="underline text-amber-300 hover:text-amber-200 font-medium"
                >
                  Use v2 instead
                </button>
                .
              </p>
              <button
                onClick={() => setBannerDismissed(true)}
                className="text-amber-400 hover:text-amber-200 shrink-0"
                aria-label="Dismiss"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
      </div>
      {/* Video player persists across page navigations */}
      {videoEnabled && (
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
      )}
      <main className="flex-1">
        {children}
      </main>
    </div>
  );
}
