"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import { sodaliteAPI } from "@/lib/api";
import { useWebSocket } from "@/hooks/useWebSocket";

interface HealthCheckContextType {
  isServerOnline: boolean;
  isConnecting: boolean;
  lastChecked: Date | null;
  heartbeats: number | null;
  connectedClients: number | null;
  totalConversions: number | null;
  totalBandwidthMB: number | null;
}

const HealthCheckContext = createContext<HealthCheckContextType | undefined>(
  undefined,
);

const WS_URL = "wss://backend.otter.llc:1335/sodalite/ws/stats";

export const HealthCheckProvider = ({ children }: { children: ReactNode }) => {
  const [isServerOnline, setIsServerOnline] = useState<boolean>(false);
  const [isConnecting, setIsConnecting] = useState<boolean>(true);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  // Use WebSocket for live stats updates
  const {
    heartbeats,
    connectedClients,
    totalConversions,
    totalBandwidthMB,
    isConnected,
  } = useWebSocket(WS_URL);

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const data = await sodaliteAPI.healthCheck();
        if (data && data.status === "ok") {
          setIsServerOnline(true);
          setIsConnecting(false);
          setLastChecked(new Date());
        }
      } catch (error) {
        setIsServerOnline(false);
        setIsConnecting(false);
      }
    };

    // Check immediately on mount
    checkStatus();

    // Then check every 30 seconds (less frequent since we have WebSocket)
    const intervalId = setInterval(checkStatus, 30000);

    return () => clearInterval(intervalId);
  }, []);

  // Update server online status based on WebSocket connection
  useEffect(() => {
    if (isConnected) {
      setIsServerOnline(true);
      setIsConnecting(false);
      setLastChecked(new Date());
    }
  }, [isConnected]);

  const value = {
    isServerOnline,
    isConnecting,
    lastChecked,
    heartbeats,
    connectedClients,
    totalConversions,
    totalBandwidthMB,
  };

  return (
    <HealthCheckContext.Provider value={value}>
      {children}
    </HealthCheckContext.Provider>
  );
};

export const useHealthCheck = (): HealthCheckContextType => {
  const context = useContext(HealthCheckContext);
  if (context === undefined) {
    throw new Error("useHealthCheck must be used within a HealthCheckProvider");
  }
  return context;
};
