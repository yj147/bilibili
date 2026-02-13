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
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/ws/logs`;
}

export function useLogStream(maxLogs = 100) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const reconnectDelay = useRef(3000);
  const isMountedRef = useRef(true);
  const isClosingRef = useRef(false);

  useEffect(() => {
    isMountedRef.current = true;
    isClosingRef.current = false;

    function connect() {
      if (!isMountedRef.current) return;

      const url = getWsUrl();
      const apiKey = process.env.NEXT_PUBLIC_API_KEY;

      if (!apiKey) {
        console.error('NEXT_PUBLIC_API_KEY is not set. WebSocket authentication will fail.');
      }

      const ws = apiKey
        ? new WebSocket(url, [`token.${apiKey}`])
        : new WebSocket(url);
      wsRef.current = ws;
      ws.onopen = () => {
        if (!isMountedRef.current || ws !== wsRef.current) return;
        setConnected(true);
        reconnectDelay.current = 3000;
        if (typeof window !== 'undefined') {
          import('sonner').then(({ toast }) => {
            toast.success('实时日志已连接');
          });
        }
      };
      ws.onerror = () => {
        if (!isMountedRef.current || ws !== wsRef.current || isClosingRef.current) return;
        console.error(`WebSocket error: ${url} (readyState: ${ws.readyState})`);
        setConnected(false);
      };
      ws.onclose = (event) => {
        if (!isMountedRef.current || ws !== wsRef.current || isClosingRef.current) return;
        console.warn(`WebSocket closed: code=${event.code}, reason="${event.reason || 'none'}"`);
        setConnected(false);
        if (typeof window !== 'undefined') {
          import('sonner').then(({ toast }) => {
            if (event.code === 1008 || event.code === 4001) {
              toast.error(`实时日志连接失败: ${event.reason || '认证失败'}`);
            } else {
              toast.warning('实时日志连接断开，正在重连...');
              reconnectRef.current = setTimeout(connect, reconnectDelay.current);
              reconnectDelay.current = Math.min(reconnectDelay.current * 2, 30000);
            }
          });
        } else if (event.code !== 1008 && event.code !== 4001) {
          reconnectRef.current = setTimeout(connect, reconnectDelay.current);
          reconnectDelay.current = Math.min(reconnectDelay.current * 2, 30000);
        }
      };
      ws.onmessage = (event) => {
        if (!isMountedRef.current || ws !== wsRef.current) return;
        try {
          const entry = JSON.parse(event.data) as LogEntry;
          if (entry.type === 'heartbeat' || entry.type === 'pong' || entry.type === 'connected') return;
          setLogs(prev => [entry, ...prev].slice(0, maxLogs));
        } catch {}
      };
    }
    connect();
    return () => {
      isMountedRef.current = false;
      isClosingRef.current = true;
      clearTimeout(reconnectRef.current);
      wsRef.current?.close();
    };
  }, [maxLogs]);

  return { logs, connected };
}
