"use client";

import { useEffect, useRef, useState } from "react";

interface PipelineVideoPlayerProps {
  videoIds: readonly string[];
}

export function PipelineVideoPlayer({ videoIds }: PipelineVideoPlayerProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const playerRef = useRef<YT.Player | null>(null);
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

    // Define the callback the API will call when ready
    (window as unknown as Record<string, unknown>).onYouTubeIframeAPIReady =
      () => {
        if (!containerRef.current) return;
        playerRef.current = new (window as unknown as { YT: typeof YT }).YT.Player(
          "yt-player",
          {
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
              onStateChange: (event: YT.OnStateChangeEvent) => {
                // Re-start when video ends (backup for loop)
                if (event.data === YT.PlayerState.ENDED) {
                  playerRef.current?.playVideo();
                }
              },
            },
          }
        );
      };

    // Only load the script once
    if (
      !(window as unknown as Record<string, unknown>).YT &&
      !document.querySelector('script[src*="youtube.com/iframe_api"]')
    ) {
      const tag = document.createElement("script");
      tag.src = "https://www.youtube.com/iframe_api";
      document.head.appendChild(tag);
    } else if ((window as unknown as Record<string, unknown>).YT) {
      // API already loaded — call the init directly
      (
        (window as unknown as Record<string, unknown>).onYouTubeIframeAPIReady as () => void
      )();
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
