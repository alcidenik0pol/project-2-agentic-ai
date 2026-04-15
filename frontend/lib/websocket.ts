/**
 * WebSocket client with reconnection logic.
 */

import type { WSMessageType } from "./types";

type MessageHandler = (message: WSMessageType) => void;

const RECONNECT_DELAY_MS = 2000;
const MAX_RECONNECT_ATTEMPTS = 5;

export class WebSocketClient {
  private url: string;
  private ws: WebSocket | null = null;
  private handler: MessageHandler;
  private reconnectAttempts = 0;
  private intentionalClose = false;

  constructor(url: string, handler: MessageHandler) {
    this.url = url;
    this.handler = handler;
  }

  connect(): void {
    this.intentionalClose = false;
    console.log(`[WebSocket] Connecting to: ${this.url}`);

    try {
      this.ws = new WebSocket(this.url);
    } catch (error) {
      console.error("[WebSocket] Failed to create WebSocket:", error);
      this.handler({
        type: "error",
        data: { message: `Failed to connect to backend: ${error}` },
      });
      return;
    }

    this.ws.onopen = () => {
      console.log("[WebSocket] Connected successfully");
      this.reconnectAttempts = 0;
      this.handler({ type: "connected", data: { run_id: "", server_time: "" } });
    };

    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as WSMessageType;
        this.handler(message);
      } catch {
        console.error("Failed to parse WebSocket message:", event.data);
      }
    };

    this.ws.onclose = () => {
      console.log(`[WebSocket] Connection closed (intentional=${this.intentionalClose}, attempts=${this.reconnectAttempts})`);
      if (!this.intentionalClose && this.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        this.reconnectAttempts++;
        console.log(`[WebSocket] Reconnecting in ${RECONNECT_DELAY_MS}ms (attempt ${this.reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`);
        setTimeout(() => this.connect(), RECONNECT_DELAY_MS);
      } else if (!this.intentionalClose) {
        this.handler({
          type: "error",
          data: { message: "WebSocket connection lost. Is the backend running on port 8901?" },
        });
      }
    };

    this.ws.onerror = (error) => {
      console.error("[WebSocket] Connection error:", error);
    };
  }

  send(message: Record<string, unknown>): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  close(): void {
    this.intentionalClose = true;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
