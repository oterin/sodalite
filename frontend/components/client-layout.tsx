"use client";

import { DownloadManager } from "@/components/download-manager";
import { GitInfo } from "@/components/git-info";
import { HealthIndicator } from "@/components/health-indicator";
import { Toaster } from "sonner";

export function ClientLayout() {
  return (
    <>
      <DownloadManager />
      <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50">
        <div className="flex items-center gap-4 px-3 py-1.5 bg-card/80 backdrop-blur-sm border border-border/50 rounded-full shadow-sm">
          <GitInfo />
          <HealthIndicator />
        </div>
      </div>
      <Toaster
        position="bottom-center"
        theme="dark"
        richColors
        expand={false}
        toastOptions={{
          className:
            "font-serif text-sm border-border/50 bg-card/95 backdrop-blur-sm",
        }}
      />
    </>
  );
}
