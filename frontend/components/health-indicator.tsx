"use client";

import { useHealthCheck } from "@/context/HealthCheckContext";
import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export function HealthIndicator() {
  const {
    isServerOnline,
    isConnecting,
    heartbeats,
    connectedClients,
    totalConversions,
    totalBandwidthMB,
  } = useHealthCheck();

  const getStatusText = () => {
    if (isConnecting) return "connecting";
    if (isServerOnline) return "online";
    return "offline";
  };

  const formatBandwidth = (mb: number | null) => {
    if (!mb || mb === 0) return "0 MB";
    if (mb < 1024) return `${mb.toFixed(1)} MB`;
    return `${(mb / 1024).toFixed(1)} GB`;
  };

  return (
    <div className="fixed top-4 right-4 z-40">
      <TooltipProvider delayDuration={150}>
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-card/80 backdrop-blur-sm border border-border/50 shadow-sm cursor-help">
              <div
                className={cn(
                  "h-2 w-2 rounded-full transition-colors",
                  isConnecting
                    ? "bg-yellow-500 animate-pulse"
                    : isServerOnline
                      ? "bg-green-500 animate-pulse-slow"
                      : "bg-destructive",
                )}
              />
              <span className="text-xs font-medium text-muted-foreground">
                {getStatusText()}
              </span>
            </div>
          </TooltipTrigger>
          <TooltipContent
            side="bottom"
            align="end"
            className="font-sans text-xs bg-card/95 backdrop-blur-sm border-border/50"
          >
            {isServerOnline ? (
              <div className="space-y-1 text-muted-foreground">
                {typeof heartbeats === "number" && (
                  <p>
                    <span className="font-semibold text-foreground">
                      {heartbeats.toLocaleString()}
                    </span>{" "}
                    heartbeats
                  </p>
                )}
                {typeof connectedClients === "number" && (
                  <p>
                    <span className="font-semibold text-foreground">
                      {connectedClients}
                    </span>{" "}
                    connected clients
                  </p>
                )}
                {typeof totalConversions === "number" && (
                  <p>
                    <span className="font-semibold text-foreground">
                      {totalConversions.toLocaleString()}
                    </span>{" "}
                    total downloads
                  </p>
                )}
                {typeof totalBandwidthMB === "number" && (
                  <p>
                    <span className="font-semibold text-foreground">
                      {formatBandwidth(totalBandwidthMB)}
                    </span>{" "}
                    total bandwidth
                  </p>
                )}
              </div>
            ) : (
              <p className="text-muted-foreground">
                {isConnecting
                  ? "Attempting to connect to server..."
                  : "Server is currently offline."}
              </p>
            )}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  );
}
