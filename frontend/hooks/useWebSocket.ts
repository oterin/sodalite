"use client";

import { useEffect, useRef, useState } from "react";
import { getWebSocketUrl } from "@/lib/api";

interface WebSocketMessage {
  type: string;
  heartbeats?: number;
  connected_clients?: number;
  total_conversions?: number;
  total_bandwidth_mb?: number;
}

interface Stats {
  heartbeats: number | null;
  connectedClients: number | null;
  totalConversions: number | null;
  totalBandwidthMB: number | null;
}

export const useWebSocket = (path: string) => {
  const [stats, setStats] = useState<Stats>({
    heartbeats: null,
    connectedClients: null,
    totalConversions: null,
    totalBandwidthMB: null,
  });
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const connect = () => {
      try {
        const url = getWebSocketUrl(path);
        const ws = new WebSocket(url);
        wsRef.current = ws;

        ws.onopen = () => {
          console.log("WebSocket connected");
          setIsConnected(true);
          // Clear any pending reconnect attempts
          if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
          }
        };

        ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);

            // handle ping messages to keep connection alive
            if (message.type === "ping") {
              return;
            }

            if (message.type === "stats") {
              setStats({
                heartbeats: message.heartbeats ?? null,
                connectedClients: message.connected_clients ?? null,
                totalConversions: message.total_conversions ?? null,
                totalBandwidthMB: message.total_bandwidth_mb ?? null,
              });
            }
          } catch (error) {
            console.error("Failed to parse WebSocket message:", error);
          }
        };

        ws.onclose = () => {
          console.log("WebSocket disconnected");
          setIsConnected(false);
          wsRef.current = null;

          // Attempt to reconnect after 5 seconds
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log("Attempting to reconnect WebSocket...");
            connect();
          }, 5000);
        };

        ws.onerror = (error) => {
          console.error("WebSocket error:", error);
          setIsConnected(false);
        };
      } catch (error) {
        console.error("Failed to create WebSocket connection:", error);
        setIsConnected(false);

        // Retry connection after 5 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, 5000);
      }
    };

    connect();

    return () => {
      // Cleanup on unmount
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [path]);

  return { ...stats, isConnected };
};
