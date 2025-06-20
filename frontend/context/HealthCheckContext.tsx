"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
  useRef,
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
  const lastSuccessfulCheck = useRef<Date | null>(null);

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const data = await sodaliteAPI.healthCheck();
        setIsServerOnline(true);
        setHeartbeats(data.heartbeats);

        // Update both refs to the same timestamp
        const now = new Date();
        lastSuccessfulCheck.current = now;
        setLastChecked(now);
      } catch (error) {
        // Server is offline, but keep the last successful heartbeat time
        setIsServerOnline(false);
        // Don't update lastChecked - it should show when we last successfully connected
        // Only update if we've never connected before
        if (lastSuccessfulCheck.current === null) {
          setLastChecked(new Date());
        } else {
          setLastChecked(lastSuccessfulCheck.current);
        }
      }
    };

    // Check immediately on mount
    checkStatus();

    // Then check every 10 seconds
    const intervalId = setInterval(checkStatus, 10000);

    // Cleanup on unmount
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
