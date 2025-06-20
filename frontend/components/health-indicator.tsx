"use client";

import { useHealthCheck } from "@/context/HealthCheckContext";
import { cn } from "@/lib/utils";

export function HealthIndicator() {
  const { isServerOnline } = useHealthCheck();

  return (
    <div
      className="fixed bottom-6 left-6 z-50"
      title={isServerOnline ? "sodalite is online" : "sodalite is offline"}
    >
      <span
        className={cn(
          "h-3 w-3 block rounded-full border-2 border-background transition-colors",
          isServerOnline
            ? "bg-green-500 animate-pulse-slow"
            : "bg-destructive",
        )}
      />
    </div>
  );
}
