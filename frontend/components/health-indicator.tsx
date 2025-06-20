"use client";

import { useState } from "react";
import { useHealthCheck } from "@/context/HealthCheckContext";
import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  ChevronUp,
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
    heartbeats,
    connectedClients,
    totalConversions,
    totalBandwidthMB,
  } = useHealthCheck();

  const formatBandwidth = (mb: number | null) => {
    if (!mb || mb === 0) return "0 MB";
    if (mb < 1024) return `${mb.toFixed(1)} MB`;
    return `${(mb / 1024).toFixed(1)} GB`;
  };

  return (
    <div className="fixed bottom-4 right-4 z-50 select-none">
      {/* Main Status Button */}
      <div
        onClick={() => setIsExpanded(!isExpanded)}
        className={cn(
          "flex items-center gap-2 px-3 py-2 rounded-full border cursor-pointer transition-all duration-200",
          "bg-card/95 backdrop-blur-sm border-border/50 shadow-lg hover:shadow-xl",
          isServerOnline
            ? "hover:bg-green-50/10 hover:border-green-500/30"
            : "hover:bg-red-50/10 hover:border-red-500/30",
        )}
      >
        {/* Status Dot */}
        <div
          className={cn(
            "h-2.5 w-2.5 rounded-full transition-colors",
            isServerOnline ? "bg-green-500 animate-pulse-slow" : "bg-red-500",
          )}
        />

        {/* Status Text */}
        <span className="text-sm font-medium text-foreground">
          {isServerOnline ? "Online" : "Offline"}
        </span>

        {/* Heartbeat Preview (only when online and collapsed) */}
        {isServerOnline && !isExpanded && typeof heartbeats === "number" && (
          <span className="text-xs font-mono text-muted-foreground bg-secondary/50 px-2 py-0.5 rounded">
            {heartbeats.toLocaleString()}
          </span>
        )}

        {/* Expand/Collapse Icon */}
        {isServerOnline && (
          <div className="text-muted-foreground">
            {isExpanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronUp className="h-4 w-4" />
            )}
          </div>
        )}
      </div>

      {/* Expanded Stats Panel */}
      {isExpanded && isServerOnline && (
        <div className="mt-2 p-4 rounded-lg border bg-card/95 backdrop-blur-sm border-border/50 shadow-xl animate-slide-up min-w-48">
          <div className="space-y-3">
            {/* Heartbeats */}
            {typeof heartbeats === "number" && (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Activity className="h-4 w-4 text-green-500" />
                  <span className="text-sm text-muted-foreground">
                    Heartbeats
                  </span>
                </div>
                <span className="text-sm font-mono font-medium">
                  {heartbeats.toLocaleString()}
                </span>
              </div>
            )}

            {/* Connected Clients */}
            {typeof connectedClients === "number" && (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Users className="h-4 w-4 text-blue-500" />
                  <span className="text-sm text-muted-foreground">Clients</span>
                </div>
                <span className="text-sm font-mono font-medium">
                  {connectedClients}
                </span>
              </div>
            )}

            {/* Total Conversions */}
            {typeof totalConversions === "number" && (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Download className="h-4 w-4 text-purple-500" />
                  <span className="text-sm text-muted-foreground">
                    Downloads
                  </span>
                </div>
                <span className="text-sm font-mono font-medium">
                  {totalConversions.toLocaleString()}
                </span>
              </div>
            )}

            {/* Total Bandwidth */}
            {typeof totalBandwidthMB === "number" && totalBandwidthMB > 0 && (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <HardDrive className="h-4 w-4 text-orange-500" />
                  <span className="text-sm text-muted-foreground">
                    Bandwidth
                  </span>
                </div>
                <span className="text-sm font-mono font-medium">
                  {formatBandwidth(totalBandwidthMB)}
                </span>
              </div>
            )}
          </div>

          {/* Close hint */}
          <div className="mt-3 pt-3 border-t border-border/50">
            <p className="text-xs text-muted-foreground text-center">
              Click to collapse
            </p>
          </div>
        </div>
      )}

      {/* Offline Tooltip */}
      {!isServerOnline && (
        <TooltipProvider delayDuration={0}>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="absolute inset-0" />
            </TooltipTrigger>
            <TooltipContent
              side="left"
              className="font-sans text-xs bg-card/95 backdrop-blur-sm border-border/50"
            >
              <p className="text-red-400">Server is offline</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}
    </div>
  );
}
