"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import type { PharmaEvent } from "@/lib/types";
import { fetchToken } from "@/lib/api";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
const MAX_BACKOFF = 30_000;

export function useEventSocket(): {
  lastEvent: PharmaEvent | null;
  connected: boolean;
} {
  const [lastEvent, setLastEvent] = useState<PharmaEvent | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const backoffRef = useRef(1000);
  const mountedRef = useRef(true);

  const connect = useCallback(async () => {
    if (!mountedRef.current) return;

    try {
      const token = await fetchToken();
      const ws = new WebSocket(`${WS_BASE}/ws/events?token=${token}`);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        backoffRef.current = 1000;
      };

      ws.onmessage = (evt) => {
        try {
          const event: PharmaEvent = JSON.parse(evt.data);
          setLastEvent(event);
        } catch {
          // ignore malformed messages
        }
      };

      ws.onclose = () => {
        setConnected(false);
        if (mountedRef.current) {
          const delay = backoffRef.current;
          backoffRef.current = Math.min(delay * 2, MAX_BACKOFF);
          setTimeout(connect, delay);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      if (mountedRef.current) {
        const delay = backoffRef.current;
        backoffRef.current = Math.min(delay * 2, MAX_BACKOFF);
        setTimeout(connect, delay);
      }
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      wsRef.current?.close();
    };
  }, [connect]);

  return { lastEvent, connected };
}
