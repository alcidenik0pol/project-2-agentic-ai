"use client";

import { useContext } from "react";
import { WebSocketContext } from "@/contexts/WebSocketContext";

export function useGlobalWebSocket() {
  return useContext(WebSocketContext);
}
