"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_LINKS } from "@/lib/nav-links";
import { useAnalysis } from "@/contexts/AnalysisContext";

export function Navbar() {
  const pathname = usePathname();
  const { dataSource, phase } = useAnalysis();

  // Disable Reddit API tab when not using a live Reddit scraper
  const isRedditApiDisabled =
    dataSource !== "reddit_live" && dataSource !== "reddit_v2" && dataSource !== "reddit_v3";
  // Big hero title shrinks once the pipeline starts (submitting → completed/failed).
  // Reset returns to idle, so the title grows back to hero size.
  const isShrunk = phase !== "idle";

  return (
    <header
      className={`flex flex-col items-center border-b border-border transition-all duration-700 ease-out ${
        isShrunk ? "py-3" : "py-8 sm:py-10"
      }`}
    >
      <Link href="/" className="flex flex-col items-center">
        <span
          className={`font-bold tracking-tight transition-all duration-700 ease-out ${
            isShrunk ? "text-lg" : "text-4xl"
          }`}
        >
          Reddit Idea Miner
        </span>
        <span
          className={`text-muted-foreground transition-all duration-700 ease-out ${
            isShrunk ? "text-[11px]" : "text-sm sm:text-base"
          }`}
        >
          Find Reddit pain points. Rank business ideas.
        </span>
      </Link>
      <nav
        className={`flex items-center gap-1 transition-all duration-700 ease-out ${
          isShrunk ? "mt-2" : "mt-4"
        }`}
      >
        {NAV_LINKS.map((link) => {
          const isActive = pathname === link.href;
          const isRedditApiLink = link.href === "/rate-limit";
          const isDisabled = isRedditApiLink && isRedditApiDisabled;

          if (isDisabled) {
            return (
              <span
                key={link.href}
                className="px-3 py-1.5 text-xs font-medium text-muted-foreground/40 cursor-not-allowed"
                title="Switch to a Reddit Scraper data source to view API status"
              >
                {link.label}
              </span>
            );
          }

          return (
            <Link
              key={link.href}
              href={link.href}
              className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                isActive
                  ? "text-foreground bg-secondary"
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
              }`}
            >
              {link.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
