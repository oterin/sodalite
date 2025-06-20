"use client";

import { useHealthCheck } from "@/context/HealthCheckContext";
import { cn } from "@/lib/utils";
import { timeAgo } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export function HealthIndicator() {
  const { isServerOnline, lastChecked, heartbeats } = useHealthCheck();

  const statusText = isServerOnline
    ? "sodalite is online"
    : "sodalite is offline";
  const lastCheckedText = lastChecked ? timeAgo(lastChecked) : "never";

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="fixed bottom-6 left-6 z-50 cursor-pointer">
            <span
              className={cn(
                "h-3 w-3 block rounded-full border-2 border-background transition-colors",
                isServerOnline
                  ? "bg-green-500 animate-pulse-slow"
                  : "bg-destructive",
              )}
            />
          </div>
        </TooltipTrigger>
        <TooltipContent
          side="right"
          className="font-serif text-xs bg-card/95 backdrop-blur-sm border-border/50"
        >
          <p className="font-medium">{statusText}</p>
          <p className="text-muted-foreground">
            last heartbeat: {lastCheckedText}
          </p>
          {isServerOnline && typeof heartbeats === "number" && (
            <p className="text-muted-foreground">
              total heartbeats: {heartbeats.toLocaleString()}
            </p>
          )}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
