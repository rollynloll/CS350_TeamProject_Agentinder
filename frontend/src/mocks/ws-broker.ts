/**
 * In-memory mock WebSocket used when VITE_USE_MOCK=true.
 *
 * Implements the small subset of the WebSocket interface that wsClient depends
 * on (open/message/close/error events, send, close, readyState, addEventListener,
 * removeEventListener). On connect it schedules a few fake events for any topic
 * the client subscribes to, so feature stubs can render live data without a server.
 */

import { uuid } from "@/lib/uuid";
import type { WsFrame } from "@/api/types";

type Listener = (evt: Event) => void;

const SUBSCRIBED_TOPICS = new Set<string>();

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
    let frame: WsFrame;
    try {
      frame = JSON.parse(raw) as WsFrame;
    } catch {
      return;
    }
    if (frame.type === "subscribe") {
      SUBSCRIBED_TOPICS.add(frame.topic);
      // Ack
      this.deliver({ type: "ack", topic: frame.topic, id: frame.id, timestamp: new Date().toISOString() });
      this.scheduleTopicEvents(frame.topic);
    } else if (frame.type === "unsubscribe") {
      SUBSCRIBED_TOPICS.delete(frame.topic);
    }
    // action frames are echoed back as events (so UI can verify round-trip)
    else if (frame.type === "action" && frame.topic.startsWith("chat.")) {
      this.deliver({
        type: "event",
        topic: frame.topic,
        id: uuid(),
        timestamp: new Date().toISOString(),
        payload: {
          kind: "message",
          message: {
            messageId: `dmsg_${uuid().slice(0, 6)}`,
            senderId: "ag_seed_001",
            type: "text",
            content: (frame.payload as { content?: string })?.content ?? "",
            sentAt: new Date().toISOString(),
          },
        },
      });
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

  private deliver(frame: WsFrame): void {
    if (this.readyState !== MockWebSocket.OPEN) return;
    const messageEvent = new MessageEvent("message", { data: JSON.stringify(frame) });
    this.dispatch("message", messageEvent);
  }

  private scheduleTopicEvents(topic: string): void {
    // date.{id} — push a fake message after 3s
    if (topic.startsWith("date.")) {
      this.timers.push(
        setTimeout(() => {
          if (!SUBSCRIBED_TOPICS.has(topic)) return;
          this.deliver({
            type: "event",
            topic,
            id: uuid(),
            timestamp: new Date().toISOString(),
            payload: {
              kind: "date_message",
              message: {
                messageId: `dmsg_${uuid().slice(0, 6)}`,
                senderId: "ag_other_101",
                content: "Sure — what is your preferred research methodology?",
                sentAt: new Date().toISOString(),
              },
            },
          });
        }, 3_000),
      );
    }
    // matches.{agentId} — push a fake new_match after 8s
    if (topic.startsWith("matches.")) {
      this.timers.push(
        setTimeout(() => {
          if (!SUBSCRIBED_TOPICS.has(topic)) return;
          this.deliver({
            type: "event",
            topic,
            id: uuid(),
            timestamp: new Date().toISOString(),
            payload: {
              kind: "new_match",
              matchId: `mt_${uuid().slice(0, 6)}`,
              partnerAgent: {
                agentId: "ag_other_103",
                displayName: "MentorMatch",
                avatarUrl: "https://api.dicebear.com/9.x/bottts/svg?seed=MentorMatch",
              },
              icebreakers: ["Welcome to your first match!"],
            },
          });
        }, 8_000),
      );
    }
  }
}
