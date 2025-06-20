"use client";

import { useState } from "react";
import { useHealthCheck } from "@/context/HealthCheckContext";
import { cn } from "@/lib/utils";
import {
  ChevronDown,
  Activity,
  Users,
  Download,
  HardDrive,
} from "lucide-react";

export function HealthIndicator() {
  const [isExpanded, setIsExpanded] = useState(false);
  const {
    isServerOnline,
    isConnecting,
    heartbeats,
    connectedClients,
    totalConversions,
    totalBandwidthMB,
  } = useHealthCheck();

  const formatBandwidth = (mb: number) => {
    if (mb < 1024) return `${mb.toFixed(1)} MB`;
    return `${(mb / 1024).toFixed(1)} GB`;
  };

  const statusText = isConnecting
    ? "connecting"
    : isServerOnline
      ? "online"
      : "offline";

  return (
    <div className="fixed top-4 right-4 z-40 select-none">
      <div className="relative">
        {/* main status button */}
        <div
          onClick={() =>
            (isServerOnline || isConnecting) && setIsExpanded(!isExpanded)
          }
          className={cn(
            "flex items-center gap-2 px-3 py-2 rounded-lg border transition-all duration-200",
            "bg-card/80 backdrop-blur-sm border-border/30 shadow-sm",
            (isServerOnline || isConnecting) &&
              "cursor-pointer hover:bg-card/90 hover:border-border/50",
          )}
        >
          <div
            className={cn(
              "h-2 w-2 rounded-full transition-colors shrink-0",
              isConnecting
                ? "bg-yellow-600/80 animate-pulse"
                : isServerOnline
                  ? "bg-green-600/80 animate-pulse-slow"
                  : "bg-destructive/80",
            )}
          />

          <span className="text-sm font-medium text-muted-foreground">
            {statusText}
          </span>

          {(isServerOnline || isConnecting) && (
            <ChevronDown
              className={cn(
                "h-3.5 w-3.5 text-muted-foreground/60 transition-transform duration-200",
                isExpanded && "rotate-180",
              )}
            />
          )}
        </div>

        {/* expanded stats card */}
        {isExpanded && (isServerOnline || isConnecting) && (
          <div className="absolute top-full right-0 mt-1 p-4 rounded-lg border bg-card/90 backdrop-blur-sm border-border/30 shadow-lg animate-slide-up w-64 sm:w-72">
            <div className="space-y-3">
              {isConnecting ? (
                <div className="text-center py-2">
                  <div className="flex items-center justify-center gap-2">
                    <div className="h-2 w-2 bg-yellow-600/80 rounded-full animate-pulse" />
                    <p className="text-sm text-muted-foreground">
                      connecting to server...
                    </p>
                  </div>
                </div>
              ) : (
                <>
                  {typeof heartbeats === "number" && (
                    <div className="flex items-center justify-between py-1">
                      <div className="flex items-center gap-3">
                        <Activity className="h-4 w-4 text-muted-foreground/60" />
                        <span className="text-sm text-muted-foreground font-medium">
                          heartbeats
                        </span>
                      </div>
                      <span className="text-sm font-mono text-foreground/80 font-medium">
                        {heartbeats.toLocaleString()}
                      </span>
                    </div>
                  )}

                  {typeof connectedClients === "number" && (
                    <div className="flex items-center justify-between py-1">
                      <div className="flex items-center gap-3">
                        <Users className="h-4 w-4 text-muted-foreground/60" />
                        <span className="text-sm text-muted-foreground font-medium">
                          connected clients
                        </span>
                      </div>
                      <span className="text-sm font-mono text-foreground/80 font-medium">
                        {connectedClients}
                      </span>
                    </div>
                  )}

                  {typeof totalConversions === "number" && (
                    <div className="flex items-center justify-between py-1">
                      <div className="flex items-center gap-3">
                        <Download className="h-4 w-4 text-muted-foreground/60" />
                        <span className="text-sm text-muted-foreground font-medium">
                          total downloads
                        </span>
                      </div>
                      <span className="text-sm font-mono text-foreground/80 font-medium">
                        {totalConversions.toLocaleString()}
                      </span>
                    </div>
                  )}

                  {typeof totalBandwidthMB === "number" && (
                    <div className="flex items-center justify-between py-1">
                      <div className="flex items-center gap-3">
                        <HardDrive className="h-4 w-4 text-muted-foreground/60" />
                        <span className="text-sm text-muted-foreground font-medium">
                          total bandwidth
                        </span>
                      </div>
                      <span className="text-sm font-mono text-foreground/80 font-medium">
                        {totalBandwidthMB > 0
                          ? formatBandwidth(totalBandwidthMB)
                          : "0 MB"}
                      </span>
                    </div>
                  )}
                </>
              )}
            </div>

            <div className="mt-4 pt-3 border-t border-border/20">
              <p className="text-xs text-muted-foreground/60 text-center">
                tap to collapse
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
