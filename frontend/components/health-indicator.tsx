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
  const {
    isServerOnline,
    heartbeats,
    connectedClients,
    totalConversions,
    totalBandwidthMB,
  } = useHealthCheck();

  const statusText = isServerOnline
    ? "sodalite is online"
    : "sodalite is offline";

  return (
    <div className="fixed bottom-6 left-6 z-50 flex items-center gap-2">
      <TooltipProvider delayDuration={0}>
        <Tooltip>
          <TooltipTrigger asChild>
            <div>
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
            side="top"
            align="start"
            sideOffset={8}
            className="font-sans text-xs text-muted-foreground bg-card/95 backdrop-blur-sm border-border/50"
            avoidCollisions={false}
          >
            <p className="font-medium text-foreground">{statusText}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      {isServerOnline && (
        <div className="flex items-center gap-2">
          {/* Heartbeats Counter */}
          {typeof heartbeats === "number" && (
            <div className="bg-card/95 backdrop-blur-sm border border-border/50 rounded-md px-2 py-1">
              <div className="flex items-center gap-1">
                <div className="h-1.5 w-1.5 bg-green-500 rounded-full animate-pulse" />
                <span className="font-mono text-xs text-muted-foreground">
                  {heartbeats.toLocaleString()}
                </span>
              </div>
            </div>
          )}

          {/* Connected Clients */}
          {typeof connectedClients === "number" && (
            <div className="bg-card/95 backdrop-blur-sm border border-border/50 rounded-md px-2 py-1">
              <div className="flex items-center gap-1">
                <div className="h-1.5 w-1.5 bg-blue-500 rounded-full" />
                <span className="font-mono text-xs text-muted-foreground">
                  {connectedClients} client{connectedClients !== 1 ? "s" : ""}
                </span>
              </div>
            </div>
          )}

          {/* Total Conversions */}
          {typeof totalConversions === "number" && (
            <div className="bg-card/95 backdrop-blur-sm border border-border/50 rounded-md px-2 py-1">
              <div className="flex items-center gap-1">
                <div className="h-1.5 w-1.5 bg-purple-500 rounded-full" />
                <span className="font-mono text-xs text-muted-foreground">
                  {totalConversions.toLocaleString()} conv
                </span>
              </div>
            </div>
          )}

          {/* Total Bandwidth */}
          {typeof totalBandwidthMB === "number" && (
            <div className="bg-card/95 backdrop-blur-sm border border-border/50 rounded-md px-2 py-1">
              <div className="flex items-center gap-1">
                <div className="h-1.5 w-1.5 bg-orange-500 rounded-full" />
                <span className="font-mono text-xs text-muted-foreground">
                  {totalBandwidthMB.toFixed(1)}MB
                </span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
