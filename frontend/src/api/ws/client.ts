import { uuid } from "@/lib/uuid";
import type { WsFrame } from "../types";

const WS_URL = import.meta.env.VITE_WS_URL ?? "wss://api.agentinder.io/v1/ws";

const HEARTBEAT_MS = 30_000;
const HEARTBEAT_FAIL_LIMIT = 3;
const RECONNECT_DELAYS = [1_000, 2_000, 4_000, 8_000, 16_000, 30_000];

export type WsStatus = "idle" | "connecting" | "open" | "closed" | "reconnecting";

export type WsHandler = (frame: WsFrame) => void;
export type StatusHandler = (status: WsStatus) => void;

/**
 * Singleton WebSocket manager.
 *
 * - Spec §4.1: query param `?token=<access_token>`
 * - Heartbeat ping every 30s; 3 consecutive failures → reconnect
 * - Exponential backoff reconnect (1, 2, 4, 8, 16, max 30s)
 * - Topic-multiplexed via subscribe/unsubscribe frames (§4.2)
 *
 * Pluggable transport via WSConstructor lets tests/Mock supply a fake socket.
 */

export type WSLike = Pick<WebSocket, "send" | "close" | "readyState"> & {
  addEventListener: WebSocket["addEventListener"];
  removeEventListener: WebSocket["removeEventListener"];
};
export type WSConstructor = new (url: string) => WSLike;

class WsClient {
  private socket: WSLike | null = null;
  private url = "";
  private tokenGetter: () => string | null = () => null;
  private wsCtor: WSConstructor = WebSocket as unknown as WSConstructor;

  private status: WsStatus = "idle";
  private statusHandlers = new Set<StatusHandler>();
  // topic → set of handlers
  private subs = new Map<string, Set<WsHandler>>();
  // topic → outstanding subscribe id (for ack tracking, optional)
  private pendingSubs = new Set<string>();

  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private heartbeatFails = 0;
  private reconnectAttempt = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private intentionalClose = false;

  configure(opts: { url?: string; tokenGetter: () => string | null; wsCtor?: WSConstructor }): void {
    this.url = opts.url ?? WS_URL;
    this.tokenGetter = opts.tokenGetter;
    if (opts.wsCtor) this.wsCtor = opts.wsCtor;
  }

  getStatus(): WsStatus {
    return this.status;
  }

  onStatus(handler: StatusHandler): () => void {
    this.statusHandlers.add(handler);
    handler(this.status);
    return () => this.statusHandlers.delete(handler);
  }

  connect(): void {
    if (this.status === "open" || this.status === "connecting") return;
    this.intentionalClose = false;
    this.setStatus(this.reconnectAttempt > 0 ? "reconnecting" : "connecting");

    const token = this.tokenGetter();
    const fullUrl = token ? `${this.url}?token=${encodeURIComponent(token)}` : this.url;

    try {
      this.socket = new this.wsCtor(fullUrl);
    } catch (err) {
      console.warn("[ws] socket construction failed; scheduling reconnect", err);
      this.scheduleReconnect();
      return;
    }

    this.socket.addEventListener("open", this.handleOpen);
    this.socket.addEventListener("message", this.handleMessage);
    this.socket.addEventListener("close", this.handleClose);
    this.socket.addEventListener("error", this.handleError);
  }

  disconnect(): void {
    this.intentionalClose = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.stopHeartbeat();
    if (this.socket) {
      try {
        this.socket.close();
      } catch {
        /* noop */
      }
      this.socket = null;
    }
    this.setStatus("closed");
  }

  subscribe(topic: string, handler: WsHandler): () => void {
    let set = this.subs.get(topic);
    if (!set) {
      set = new Set();
      this.subs.set(topic, set);
      // First subscriber for this topic → send subscribe frame
      this.sendFrame({ type: "subscribe", topic });
      this.pendingSubs.add(topic);
    }
    set.add(handler);

    return () => {
      const current = this.subs.get(topic);
      if (!current) return;
      current.delete(handler);
      if (current.size === 0) {
        this.subs.delete(topic);
        this.sendFrame({ type: "unsubscribe", topic });
      }
    };
  }

  send(topic: string, payload: unknown): void {
    this.sendFrame({ type: "action", topic, payload });
  }

  // ---- internal ----

  private handleOpen = (): void => {
    this.reconnectAttempt = 0;
    this.heartbeatFails = 0;
    this.setStatus("open");
    // Re-subscribe to all topics on (re)connect
    for (const topic of this.subs.keys()) {
      this.sendFrame({ type: "subscribe", topic });
    }
    this.startHeartbeat();
  };

  private handleMessage = (evt: Event): void => {
    const data = (evt as MessageEvent).data;
    if (typeof data !== "string") return;
    let frame: WsFrame;
    try {
      frame = JSON.parse(data) as WsFrame;
    } catch {
      return;
    }
    if (frame.type === "ack" && this.pendingSubs.has(frame.topic)) {
      this.pendingSubs.delete(frame.topic);
      return;
    }
    if (frame.type === "event" || frame.type === "ack") {
      const handlers = this.subs.get(frame.topic);
      if (!handlers) return;
      for (const h of handlers) {
        try {
          h(frame);
        } catch (err) {
          console.error("[ws] handler error", err);
        }
      }
    }
  };

  private handleClose = (): void => {
    this.stopHeartbeat();
    this.socket = null;
    if (this.intentionalClose) {
      this.setStatus("closed");
      return;
    }
    this.scheduleReconnect();
  };

  private handleError = (err: Event): void => {
    console.warn("[ws] error event", err);
  };

  private scheduleReconnect(): void {
    this.setStatus("reconnecting");
    const delay = RECONNECT_DELAYS[Math.min(this.reconnectAttempt, RECONNECT_DELAYS.length - 1)];
    this.reconnectAttempt += 1;
    this.reconnectTimer = setTimeout(() => this.connect(), delay);
  }

  private sendFrame(partial: { type: WsFrame["type"]; topic: string; payload?: unknown }): void {
    const frame: WsFrame = {
      type: partial.type,
      topic: partial.topic,
      payload: partial.payload,
      id: uuid(),
      timestamp: new Date().toISOString(),
    };
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(frame));
    }
    // If socket not ready: subscribe frames will be replayed in handleOpen
  }

  private setStatus(s: WsStatus): void {
    if (this.status === s) return;
    this.status = s;
    for (const h of this.statusHandlers) h(s);
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
        this.heartbeatFails += 1;
      } else {
        this.sendFrame({ type: "action", topic: "_ping" });
        // Without server pong tracking we optimistically reset on send success.
        this.heartbeatFails = 0;
      }
      if (this.heartbeatFails >= HEARTBEAT_FAIL_LIMIT) {
        this.heartbeatFails = 0;
        this.disconnect();
        this.intentionalClose = false;
        this.scheduleReconnect();
      }
    }, HEARTBEAT_MS);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }
}

export const wsClient = new WsClient();
