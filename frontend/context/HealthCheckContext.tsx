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
}

const HealthCheckContext = createContext<HealthCheckContextType | undefined>(
  undefined,
);

export const HealthCheckProvider = ({ children }: { children: ReactNode }) => {
  const [isServerOnline, setIsServerOnline] = useState<boolean>(true);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  useEffect(() => {
    const checkStatus = async () => {
      try {
        // This function will be added to the api.ts file later
        await sodaliteAPI.healthCheck();
        setIsServerOnline(true);
      } catch (error) {
        // We can safely assume a failed request means the server is offline
        setIsServerOnline(false);
      } finally {
        setLastChecked(new Date());
      }
    };

    // Check immediately on mount
    checkStatus();

    // Then check every 30 seconds
    const intervalId = setInterval(checkStatus, 30000);

    // Cleanup on unmount
    return () => clearInterval(intervalId);
  }, []);

  const value = { isServerOnline, lastChecked };

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
