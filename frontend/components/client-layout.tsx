"use client";

import { DownloadManager } from "@/components/download-manager";
import { GitInfo } from "@/components/git-info";
import { HealthIndicator } from "@/components/health-indicator";
import { Toaster } from "sonner";

/**
 * this component wraps all the floating, client-side ui elements
 * that should persist across all pages.
 *
 * each component handles its own positioning and visibility logic internally.
 */
export function ClientLayout() {
  return (
    <>
      <GitInfo />
      <HealthIndicator />
      <DownloadManager />

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
