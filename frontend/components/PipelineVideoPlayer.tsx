"use client";

import { useEffect, useRef, useState } from "react";

/* eslint-disable @typescript-eslint/no-explicit-any */

interface PipelineVideoPlayerProps {
  videoIds: readonly string[];
}

// YouTube PlayerState.ENDED === 0
const YT_PLAYER_STATE_ENDED = 0;

export function PipelineVideoPlayer({ videoIds }: PipelineVideoPlayerProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const playerRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Pick a random video once on mount
  useEffect(() => {
    if (videoIds.length === 0) return;
    const idx = Math.floor(Math.random() * videoIds.length);
    setSelectedId(videoIds[idx]);
  }, [videoIds]);

  // Load YouTube IFrame API and create player
  useEffect(() => {
    if (!selectedId) return;

    const w = window as any;

    // Define the callback the API will call when ready
    w.onYouTubeIframeAPIReady = () => {
      if (!containerRef.current) return;
      playerRef.current = new w.YT.Player("yt-player", {
        videoId: selectedId,
        playerVars: {
          autoplay: 1,
          loop: 1,
          playlist: selectedId, // required for loop to work
          mute: 1, // muted required for autoplay in most browsers
          controls: 1,
          modestbranding: 1,
          rel: 0,
        },
        events: {
          onStateChange: (event: any) => {
            // Re-start when video ends (backup for loop)
            if (event.data === YT_PLAYER_STATE_ENDED) {
              playerRef.current?.playVideo();
            }
          },
        },
      });
    };

    // Only load the script once
    if (!w.YT && !document.querySelector('script[src*="youtube.com/iframe_api"]')) {
      const tag = document.createElement("script");
      tag.src = "https://www.youtube.com/iframe_api";
      document.head.appendChild(tag);
    } else if (w.YT) {
      // API already loaded — call the init directly
      w.onYouTubeIframeAPIReady();
    }

    return () => {
      playerRef.current?.destroy();
      playerRef.current = null;
    };
  }, [selectedId]);

  if (!selectedId) return null;

  return (
    <div className="w-full max-w-[700px] mb-4 border border-border bg-card overflow-hidden">
      <div className="px-4 pt-3 pb-2 border-b border-border">
        <span className="text-xs text-muted-foreground">
          While you wait...
        </span>
      </div>
      <div className="relative w-full" style={{ paddingBottom: "56.25%" }}>
        <div
          ref={containerRef}
          id="yt-player"
          className="absolute inset-0"
        />
      </div>
    </div>
  );
}
