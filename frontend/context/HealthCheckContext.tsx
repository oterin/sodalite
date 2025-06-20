"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import { sodaliteAPI } from "@/lib/api";

interface HealthCheckContextType {
  isServerOnline: boolean;
  lastChecked: Date | null;
  heartbeats: number | null;
}

const HealthCheckContext = createContext<HealthCheckContextType | undefined>(
  undefined,
);

export const HealthCheckProvider = ({ children }: { children: ReactNode }) => {
  const [isServerOnline, setIsServerOnline] = useState<boolean>(true);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const [heartbeats, setHeartbeats] = useState<number | null>(null);

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const data = await sodaliteAPI.healthCheck();
        setIsServerOnline(true);
        setHeartbeats(data.heartbeats);
        setLastChecked(new Date());
      } catch (error) {
        // we can safely assume a failed request means the server is offline
        setIsServerOnline(false);
      }
    };

    // check immediately on mount
    checkStatus();

    // then check every 10 seconds
    const intervalId = setInterval(checkStatus, 10000);

    // cleanup on unmount
    return () => clearInterval(intervalId);
  }, []);

  const value = { isServerOnline, lastChecked, heartbeats };

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
