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
 * Speaks the FastAPI backend's WS protocol (backend/app/transport/ws_transport.py):
 *   client → server : { event: "subscribe"|"unsubscribe", topic } and
 *                      { event: "send_message"|"join_date", payload: {...} }
 *   server → client : flat events keyed by `event`, e.g.
 *                      { event: "message", message_id, match_id, sender_agent_id, content }
 *                      { event: "subscribed", topic } (subscribe reply)
 *
 * Incoming pushes carry no `topic` field, so `adaptIncoming` derives the topic
 * (e.g. chat.{match_id}) and maps the flat payload into the `{ kind, ... }`
 * shape feature handlers expect. The Mock broker (mocks/ws-broker.ts) mirrors
 * this exact protocol so dev-on-mock and real backend behave identically.
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
      this.sendRaw({ event: "subscribe", topic });
      this.pendingSubs.add(topic);
    }
    set.add(handler);

    return () => {
      const current = this.subs.get(topic);
      if (!current) return;
      current.delete(handler);
      if (current.size === 0) {
        this.subs.delete(topic);
        this.sendRaw({ event: "unsubscribe", topic });
      }
    };
  }

  /**
   * Send a backend action frame, e.g.
   *   sendAction("send_message", { match_id, agent_id, content })
   *   sendAction("join_date",    { date_id, agent_id })
   */
  sendAction(event: string, payload: Record<string, unknown>): void {
    this.sendRaw({ event, payload });
  }

  // ---- internal ----

  private handleOpen = (): void => {
    this.reconnectAttempt = 0;
    this.heartbeatFails = 0;
    this.setStatus("open");
    // Re-subscribe to all topics on (re)connect
    for (const topic of this.subs.keys()) {
      this.sendRaw({ event: "subscribe", topic });
      this.pendingSubs.add(topic);
    }
    this.startHeartbeat();
  };

  private handleMessage = (evt: Event): void => {
    const data = (evt as MessageEvent).data;
    if (typeof data !== "string") return;
    let raw: Record<string, unknown>;
    try {
      raw = JSON.parse(data) as Record<string, unknown>;
    } catch {
      return;
    }

    const event = raw.event as string | undefined;

    // Subscribe ack / control replies and direct send replies — not topic events.
    if (event === "subscribed") {
      this.pendingSubs.delete(raw.topic as string);
      return;
    }
    if (event === "unsubscribed") return;
    if (event === "message_sent" || event === "date_joined") return;
    if (raw.error) {
      console.warn("[ws] server error:", raw.error);
      return;
    }
    if (!event) return;

    // Topic-bound push — derive topic + adapt to the { kind, ... } shape.
    const adapted = this.adaptIncoming(event, raw);
    if (!adapted) return;

    const frame: WsFrame = {
      type: "event",
      topic: adapted.topic,
      payload: adapted.payload,
      id: uuid(),
      timestamp: new Date().toISOString(),
    };

    const targets =
      adapted.topic === "*"
        ? [...this.subs.values()]
        : this.subs.has(adapted.topic)
          ? [this.subs.get(adapted.topic)!]
          : [];
    for (const handlers of targets) {
      for (const h of handlers) {
        try {
          h(frame);
        } catch (err) {
          console.error("[ws] handler error", err);
        }
      }
    }
  };

  /**
   * Map a flat backend event into (topic, frontend-shaped payload).
   * Returns null for events with no client-side topic (e.g. notifications).
   * topic === "*" means "deliver to every matching subscription" (used for
   * new_match, which the backend keys by principal id rather than agent id).
   */
  private adaptIncoming(
    event: string,
    raw: Record<string, unknown>,
  ): { topic: string; payload: unknown } | null {
    switch (event) {
      case "message":
        return {
          topic: `chat.${raw.match_id}`,
          payload: {
            kind: "message",
            message: {
              messageId: String(raw.message_id ?? uuid()),
              senderId: String(raw.sender_agent_id ?? ""),
              type: "text",
              content: String(raw.content ?? ""),
              sentAt: (raw.sent_at as string) ?? new Date().toISOString(),
            },
          },
        };
      case "new_match":
        // Backend keys this by principal id; fan out to all matches.* subs.
        return {
          topic: "*",
          payload: { kind: "new_match", matchId: String(raw.match_id ?? "") },
        };
      case "date_started":
        return {
          topic: `date.${raw.date_id}`,
          payload: { kind: "date_started", dateId: String(raw.date_id ?? "") },
        };
      case "date_ended":
        return {
          topic: `date.${raw.date_id}`,
          payload: {
            kind: "date_ended",
            outcome: String(raw.outcome ?? ""),
            endedBy: "",
          },
        };
      default:
        return null;
    }
  }

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

  /** Emit a backend-shaped frame ({ event, topic?, payload? }). */
  private sendRaw(frame: Record<string, unknown>): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(frame));
    }
    // If socket not ready: subscribe frames are replayed in handleOpen.
  }

  private setStatus(s: WsStatus): void {
    if (this.status === s) return;
    this.status = s;
    for (const h of this.statusHandlers) h(s);
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      // Backend has no ping handler, so we only monitor socket health rather
      // than emitting a frame (a junk frame would draw an error reply).
      if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
        this.heartbeatFails += 1;
      } else {
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
