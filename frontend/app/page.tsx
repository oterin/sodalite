"use client";

import { useState } from "react";
import { DownloadForm } from "@/components/download-form";
import { ServiceBadges } from "@/components/service-badges";
import { DownloadProgress } from "@/components/download-progress";
import { QualitySelector } from "@/components/quality-selector";
import {
  sodaliteAPI,
  type DownloadMetadata,
  type ProcessResponse,
} from "@/lib/api";
import { toast } from "sonner";

export default function Home() {
  const [metadata, setMetadata] = useState<DownloadMetadata | null>(null);
  const [task, setTask] = useState<ProcessResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleUrlSubmit = async (url: string) => {
    setIsLoading(true);
    setMetadata(null);
    setTask(null);

    try {
      const data = await sodaliteAPI.getDownloadInfo(url);
      setMetadata(data);
      toast.success("Meta found! Select quality to download.");
    } catch (error: any) {
      const errorMessage =
        error.response?.data?.detail?.error || "Failed to fetch media info";
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container relative mx-auto flex min-h-screen flex-col items-center justify-center px-4">
      <div className="w-full max-w-2xl space-y-8">
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold tracking-tighter sm:text-5xl">
            sodalite
          </h1>
          <p className="text-muted-foreground">
            a simple downloader for the web
          </p>
        </div>

        <DownloadForm onSubmit={handleUrlSubmit} isLoading={isLoading} />
        <ServiceBadges />

        {metadata && (
          <QualitySelector metadata={metadata} onTaskCreated={setTask} />
        )}
        {task && <DownloadProgress task={task} />}
      </div>
    </div>
  );
}
