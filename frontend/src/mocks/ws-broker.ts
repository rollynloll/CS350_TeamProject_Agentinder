/**
 * In-memory mock WebSocket used when VITE_USE_MOCK=true.
 *
 * Mirrors the FastAPI backend WS protocol (backend/app/transport/ws_transport.py)
 * so behaviour on mock matches the real backend:
 *   client → server : { event: "subscribe"|"unsubscribe", topic } /
 *                      { event: "send_message", payload: { match_id, agent_id, content } }
 *   server → client : { event: "subscribed", topic } and flat topic pushes like
 *                      { event: "message", message_id, match_id, sender_agent_id, content }
 *
 * Implements only the subset of WebSocket that wsClient depends on.
 */

import { uuid } from "@/lib/uuid";

type Listener = (evt: Event) => void;

const SUBSCRIBED_TOPICS = new Set<string>();

const CANNED_REPLIES = [
  "Exactly — that lines up with how I work too. Want to set up a coffee chat?",
  "Good point. I can take the structured side while you handle the open-ended parts.",
  "Agreed. Let's pin down a time that works for both of us.",
];

export class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  url: string;

  private listeners: Record<string, Set<Listener>> = {
    open: new Set(),
    message: new Set(),
    close: new Set(),
    error: new Set(),
  };
  private timers: ReturnType<typeof setTimeout>[] = [];
  private replyIdx = 0;

  constructor(url: string) {
    this.url = url;
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      this.dispatch("open", new Event("open"));
    }, 50);
  }

  addEventListener(type: string, listener: Listener): void {
    this.listeners[type]?.add(listener);
  }

  removeEventListener(type: string, listener: Listener): void {
    this.listeners[type]?.delete(listener);
  }

  send(raw: string): void {
    let frame: Record<string, unknown>;
    try {
      frame = JSON.parse(raw) as Record<string, unknown>;
    } catch {
      return;
    }
    const event = frame.event as string | undefined;
    const topic = frame.topic as string | undefined;
    const payload = (frame.payload ?? {}) as Record<string, unknown>;

    if (event === "subscribe" && topic) {
      SUBSCRIBED_TOPICS.add(topic);
      this.deliver({ event: "subscribed", topic });
      this.scheduleTopicEvents(topic);
    } else if (event === "unsubscribe" && topic) {
      SUBSCRIBED_TOPICS.delete(topic);
    } else if (event === "send_message") {
      // Backend saves the user message (no echo) then generates an agent reply
      // and pushes it to chat.{match_id}. Mock the reply only.
      const matchId = String(payload.match_id ?? "");
      const chatTopic = `chat.${matchId}`;
      const content =
        CANNED_REPLIES[this.replyIdx++ % CANNED_REPLIES.length];
      this.deliver({ event: "message_sent", response: content, message_id: uuid() });
      this.timers.push(
        setTimeout(() => {
          if (!SUBSCRIBED_TOPICS.has(chatTopic)) return;
          this.deliver({
            event: "message",
            message_id: uuid(),
            match_id: matchId,
            // Partner agent replies (renders left/white). Backend currently
            // attributes the auto-reply to the sender's own agent — flagged.
            sender_agent_id: "ag_other_101",
            content,
          });
        }, 1_200),
      );
    }
  }

  close(): void {
    if (this.readyState === MockWebSocket.CLOSED) return;
    this.readyState = MockWebSocket.CLOSED;
    this.timers.forEach((t) => clearTimeout(t));
    this.timers = [];
    this.dispatch("close", new Event("close"));
  }

  private dispatch(type: string, evt: Event): void {
    this.listeners[type]?.forEach((l) => l(evt));
  }

  private deliver(frame: Record<string, unknown>): void {
    if (this.readyState !== MockWebSocket.OPEN) return;
    const messageEvent = new MessageEvent("message", { data: JSON.stringify(frame) });
    this.dispatch("message", messageEvent);
  }

  private scheduleTopicEvents(topic: string): void {
    // matches.{agentId} — push a fake new_match after 8s (backend MatchCreated).
    if (topic.startsWith("matches.")) {
      this.timers.push(
        setTimeout(() => {
          if (!SUBSCRIBED_TOPICS.has(topic)) return;
          this.deliver({ event: "new_match", match_id: `mt_${uuid().slice(0, 6)}` });
        }, 8_000),
      );
    }
  }
}
