import { useEffect, useRef, useState } from 'react';

export interface LogEntry {
  type: string;
  message: string;
  data: Record<string, unknown>;
  timestamp: number;
}

function getWsUrl() {
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL;
  if (wsUrl) return wsUrl;
  if (typeof window === 'undefined') return 'ws://localhost:8000/ws/logs';
  // In production, use same host; in dev (port 3000), connect to backend directly
  const isDev = window.location.port === '3000';
  if (isDev) return 'ws://localhost:8000/ws/logs';
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/ws/logs`;
}

export function useLogStream(maxLogs = 100) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    function connect() {
      let url = getWsUrl();
      const apiKey = process.env.NEXT_PUBLIC_API_KEY;
      if (apiKey) url += `?token=${apiKey}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;
      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        reconnectRef.current = setTimeout(connect, 3000);
      };
      ws.onmessage = (event) => {
        try {
          const entry = JSON.parse(event.data) as LogEntry;
          if (entry.type === 'heartbeat' || entry.type === 'pong' || entry.type === 'connected') return;
          setLogs(prev => [entry, ...prev].slice(0, maxLogs));
        } catch {}
      };
    }
    connect();
    return () => {
      clearTimeout(reconnectRef.current);
      wsRef.current?.close();
    };
  }, [maxLogs]);

  return { logs, connected };
}
