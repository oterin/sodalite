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

  const getStatusText = () => {
    if (isConnecting) return "connecting";
    return isServerOnline ? "online" : "offline";
  };

  const canExpand = isServerOnline || isConnecting;

  return (
    <div className="fixed top-4 right-4 z-40 select-none">
      <div className="relative">
        {/* status button */}
        <div
          onClick={() => canExpand && setIsExpanded(!isExpanded)}
          className={cn(
            "flex items-center gap-2 px-3 py-2 rounded-lg border transition-all duration-200",
            "bg-card/80 backdrop-blur-sm border-border/30 shadow-sm",
            canExpand &&
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
            {getStatusText()}
          </span>

          {canExpand && (
            <div
              className={cn(
                "text-muted-foreground/60 shrink-0 transition-transform duration-200",
                isExpanded && "rotate-180",
              )}
            >
              <ChevronDown className="h-3.5 w-3.5" />
            </div>
          )}
        </div>

        {/* dropdown card */}
        {isExpanded && canExpand && (
          <div className="absolute top-full right-0 mt-2 p-3 rounded-lg border bg-card/90 backdrop-blur-sm border-border/30 shadow-lg w-60 sm:w-64 animate-slide-up">
            {isConnecting ? (
              <div className="text-center py-3">
                <div className="flex items-center justify-center gap-2">
                  <div className="h-2 w-2 bg-yellow-600/80 rounded-full animate-pulse" />
                  <p className="text-sm text-muted-foreground">
                    connecting to server...
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                {typeof heartbeats === "number" && (
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Activity className="h-3.5 w-3.5 text-muted-foreground/60" />
                      <span className="text-xs text-muted-foreground">
                        heartbeats
                      </span>
                    </div>
                    <span className="text-xs font-mono text-foreground/80">
                      {heartbeats.toLocaleString()}
                    </span>
                  </div>
                )}

                {typeof connectedClients === "number" && (
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Users className="h-3.5 w-3.5 text-muted-foreground/60" />
                      <span className="text-xs text-muted-foreground">
                        clients
                      </span>
                    </div>
                    <span className="text-xs font-mono text-foreground/80">
                      {connectedClients}
                    </span>
                  </div>
                )}

                {typeof totalConversions === "number" && (
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Download className="h-3.5 w-3.5 text-muted-foreground/60" />
                      <span className="text-xs text-muted-foreground">
                        downloads
                      </span>
                    </div>
                    <span className="text-xs font-mono text-foreground/80">
                      {totalConversions.toLocaleString()}
                    </span>
                  </div>
                )}

                {typeof totalBandwidthMB === "number" && (
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <HardDrive className="h-3.5 w-3.5 text-muted-foreground/60" />
                      <span className="text-xs text-muted-foreground">
                        bandwidth
                      </span>
                    </div>
                    <span className="text-xs font-mono text-foreground/80">
                      {totalBandwidthMB > 0
                        ? formatBandwidth(totalBandwidthMB)
                        : "0 MB"}
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
