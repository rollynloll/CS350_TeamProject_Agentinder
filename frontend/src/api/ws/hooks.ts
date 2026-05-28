import { useEffect, useState } from "react";
import type { WsFrame } from "../types";
import { wsClient, type WsStatus } from "./client";

export function useWsStatus(): WsStatus {
  const [status, setStatus] = useState<WsStatus>(wsClient.getStatus());
  useEffect(() => wsClient.onStatus(setStatus), []);
  return status;
}

/**
 * Subscribe to a topic for the lifetime of the component.
 * Pass `null` topic to disable (e.g. when route params not yet ready).
 */
export function useTopic(topic: string | null, handler: (frame: WsFrame) => void): void {
  useEffect(() => {
    if (!topic) return;
    const unsub = wsClient.subscribe(topic, handler);
    return unsub;
    // handler intentionally not in deps — callers should memoize if needed.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topic]);
}
