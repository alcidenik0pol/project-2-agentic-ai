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
  private _isReplaced = false;

  constructor(url: string, handler: MessageHandler) {
    this.url = url;
    this.handler = handler;
  }

  connect(): void {
    this.intentionalClose = false;
    console.log(`[WSClient] connect() called — url=${this.url}, isReplaced=${this._isReplaced}, attempts=${this.reconnectAttempts}`);

    try {
      this.ws = new WebSocket(this.url);
      console.log(`[WSClient] WebSocket instance created, readyState=${this.ws.readyState}`);
    } catch (error) {
      console.error("[WSClient] Failed to create WebSocket:", error);
      this.handler({
        type: "error",
        data: { message: `Failed to connect to backend: ${error}` },
      });
      return;
    }

    this.ws.onopen = () => {
      console.log("[WSClient] onopen — Connected successfully");
      this.reconnectAttempts = 0;
      this.handler({ type: "connected", data: { run_id: "", server_time: "" } });
    };

    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as WSMessageType;
        console.log(`[WSClient] onmessage: type=${message.type}`, message.data);
        this.handler(message);
      } catch (err) {
        console.error("[WSClient] Failed to parse WebSocket message:", event.data, err);
      }
    };

    this.ws.onclose = (event) => {
      console.log(`[WSClient] onclose: code=${event.code}, reason=${event.reason}, wasClean=${event.wasClean}, isReplaced=${this._isReplaced}, intentional=${this.intentionalClose}`);
      if (this._isReplaced) {
        console.log("[WSClient] onclose — replaced by new connection, ignoring");
        return;
      }
      console.log(`[WSClient] onclose — attempts=${this.reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS}`);
      if (!this.intentionalClose && this.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        this.reconnectAttempts++;
        console.log(`[WSClient] Reconnecting in ${RECONNECT_DELAY_MS}ms (attempt ${this.reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`);
        setTimeout(() => this.connect(), RECONNECT_DELAY_MS);
      } else if (!this.intentionalClose) {
        console.error("[WSClient] Max reconnect attempts reached — giving up");
        this.handler({
          type: "connection_lost",
          data: { message: "WebSocket connection lost. Results may still be loading." },
        });
      }
    };

    this.ws.onerror = (error) => {
      console.error("[WSClient] onerror:", error);
    };
  }

  send(message: Record<string, unknown>): void {
    console.log(`[WSClient] send(): type=${message.type}, readyState=${this.ws?.readyState}, isReplaced=${this._isReplaced}`);
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn("[WSClient] send(): cannot send — socket not open", {
        readyState: this.ws?.readyState,
        isReplaced: this._isReplaced,
      });
    }
  }

  /** Mark this client as replaced so its onclose handler won't interfere with the new connection. */
  markReplaced(): void {
    console.log(`[WSClient] markReplaced() — was already replaced: ${this._isReplaced}`);
    this._isReplaced = true;
  }

  close(): void {
    console.log(`[WSClient] close() called — intentional=${this.intentionalClose}, hadWs=${!!this.ws}`);
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
