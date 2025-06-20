"use client";

import { useState } from "react";
import { DownloadForm } from "@/components/download-form";
import { ServiceBadges } from "@/components/service-badges";
import { ResultsDialog } from "@/components/results-dialog";
import { sodaliteAPI, type SanitizedDownloadMetadata } from "@/lib/api";
import { toast } from "sonner";
import axios from "axios";
import { useHealthCheck } from "@/context/HealthCheckContext";
import { ServerStatus } from "@/components/server-status";
import { NewsBanner } from "@/components/news-banner";

export default function Home() {
  const [metadata, setMetadata] = useState<SanitizedDownloadMetadata | null>(
    null,
  );
  const [currentUrl, setCurrentUrl] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const { isServerOnline, isConnecting } = useHealthCheck();

  const isOffline = !isServerOnline && !isConnecting;

  const handleUrlSubmit = async (url: string) => {
    setIsLoading(true);
    setMetadata(null);
    setCurrentUrl(url);

    try {
      const data = await sodaliteAPI.getDownloadInfo(url);
      setMetadata(data);
      toast.success("found it! here are the details.");
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const errorMessage =
          error.response?.data?.detail?.error ||
          error.response?.data?.detail ||
          "failed to fetch media information.";
        toast.error(errorMessage);
      } else {
        toast.error("an unexpected error occurred.");
      }
      console.error("Error fetching download info:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setMetadata(null);
    setCurrentUrl("");
  };

  return (
    <>
      <div className="container relative mx-auto flex min-h-screen flex-col items-center justify-center px-4 py-8">
        <div className="absolute top-8 left-4 right-4 z-10 mx-auto max-w-lg">
          <NewsBanner isServerOnline={isServerOnline} />
        </div>

        <div className="w-full max-w-lg space-y-6">
          {isOffline ? (
            <ServerStatus />
          ) : (
            <>
              <div className="text-center space-y-3 animate-fade-in">
                <h1 className="text-4xl sm:text-5xl font-serif font-bold tracking-tight">
                  sodalite
                </h1>
                <p className="text-lg text-muted-foreground">
                  a friendly media downloader
                </p>
              </div>

              <div className="space-y-6 animate-slide-up">
                <DownloadForm
                  onSubmit={handleUrlSubmit}
                  isLoading={isLoading}
                />
                <ServiceBadges />
              </div>
            </>
          )}
        </div>
      </div>

      <ResultsDialog
        metadata={metadata}
        url={currentUrl}
        onOpenChange={handleReset}
        thumbnailUrl={metadata?.thumbnail_url}
      />
    </>
  );
}
