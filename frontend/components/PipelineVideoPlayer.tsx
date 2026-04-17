"use client";

import { useEffect, useRef, useState } from "react";

/* eslint-disable @typescript-eslint/no-explicit-any */

interface PipelineVideoPlayerProps {
  videoIds: readonly string[];
  active: boolean;
}

// YouTube PlayerState.ENDED === 0
const YT_PLAYER_STATE_ENDED = 0;

export function PipelineVideoPlayer({ videoIds, active }: PipelineVideoPlayerProps) {
  const [shuffled, setShuffled] = useState<string[]>([]);
  const [currentIndex, setCurrentIndex] = useState<number>(-1);
  const [visible, setVisible] = useState(true);
  const playerRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Shuffle the playlist once on mount (Fisher-Yates)
  useEffect(() => {
    if (videoIds.length === 0 || shuffled.length > 0) return;
    const arr = [...videoIds];
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    setShuffled(arr);
    setCurrentIndex(0);
  }, [videoIds, shuffled.length]);

  const selectedId = currentIndex >= 0 && shuffled.length > 0 ? shuffled[currentIndex] : null;

  // Load YouTube IFrame API and create player
  useEffect(() => {
    if (!selectedId) return;

    const w = window as any;

    const createPlayer = () => {
      if (!containerRef.current) return;
      playerRef.current = new w.YT.Player("yt-player", {
        videoId: selectedId,
        playerVars: {
          autoplay: 1,
          mute: 0,
          controls: 1,
          modestbranding: 1,
          rel: 0,
        },
        events: {
          onStateChange: (event: any) => {
            if (event.data === YT_PLAYER_STATE_ENDED) {
              setCurrentIndex((i) => (i + 1) % shuffled.length);
            }
          },
        },
      });
    };

    w.onYouTubeIframeAPIReady = createPlayer;

    if (!w.YT && !document.querySelector('script[src*="youtube.com/iframe_api"]')) {
      const tag = document.createElement("script");
      tag.src = "https://www.youtube.com/iframe_api";
      document.head.appendChild(tag);
    } else if (w.YT) {
      createPlayer();
    }

    return () => {
      playerRef.current?.destroy();
      playerRef.current = null;
    };
  }, [selectedId, shuffled.length]);

  // Pause when pipeline completes, resume if it restarts
  useEffect(() => {
    if (!playerRef.current) return;
    if (active) {
      playerRef.current.playVideo();
    } else {
      playerRef.current.pauseVideo();
    }
  }, [active]);

  if (!selectedId) return null;

  return (
    <div className="w-full max-w-[700px] mb-4 border border-border bg-card overflow-hidden">
      <div className="px-4 pt-3 pb-2 border-b border-border flex items-center justify-between">
        <span className="text-xs text-muted-foreground">
          While you wait... Here is some AI (and non-AI) slop
        </span>
        <button
          onClick={() => setVisible((v) => !v)}
          className="text-xs text-muted-foreground hover:text-foreground transition-colors px-2 py-0.5 border border-border"
        >
          {visible ? "Hide" : "Show"}
        </button>
      </div>
      {/* iframe stays in DOM when hidden so audio keeps playing */}
      <div
        style={{
          position: "relative",
          width: "100%",
          paddingBottom: visible ? "56.25%" : "0",
          overflow: "hidden",
          height: visible ? "auto" : "0",
        }}
      >
        <div
          ref={containerRef}
          id="yt-player"
          style={{
            position: visible ? "absolute" : "relative",
            inset: visible ? 0 : undefined,
            width: visible ? "100%" : "1px",
            height: visible ? "100%" : "1px",
            opacity: visible ? 1 : 0,
            pointerEvents: visible ? "auto" : "none",
          }}
        />
      </div>
    </div>
  );
}
