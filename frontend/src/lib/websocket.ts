import { useEffect, useRef, useState } from 'react';

export interface LogEntry {
  type: string;
  message: string;
  data: Record<string, any>;
  timestamp: number;
}

export function useLogStream(maxLogs = 100) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    function connect() {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const ws = new WebSocket(`${protocol}//${window.location.host}/ws/logs`);
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
