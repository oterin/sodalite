"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import axios from "axios";
import { toast } from "sonner";
import {
  Download,
  Video,
  Loader2,
  FileVideo,
  FileAudio,
  X,
  Film,
  Music,
  VolumeX,
  Image as ImageIcon,
} from "lucide-react";

import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { VisuallyHidden } from "@/components/ui/visually-hidden";
import { sodaliteAPI, type SanitizedDownloadMetadata } from "@/lib/api";
import { useDownloads } from "@/context/DownloadContext";

interface ResultsDialogProps {
  metadata: SanitizedDownloadMetadata | null;
  url: string;
  onOpenChange: () => void;
  thumbnailUrl?: string;
}

type DownloadMode = "default" | "video_only" | "audio_only";

export function ResultsDialog({
  metadata,
  url,
  onOpenChange,
  thumbnailUrl,
}: ResultsDialogProps) {
  const { addTask } = useDownloads();
  const [isOpen, setIsOpen] = useState(false);
  const [selectedVideo, setSelectedVideo] = useState<string | undefined>();
  const [selectedAudio, setSelectedAudio] = useState<string | undefined>();
  const [downloadMode, setDownloadMode] = useState<DownloadMode>("default");
  const [format, setFormat] = useState<string>("mp4");
  const [isProcessing, setIsProcessing] = useState(false);
  const isPhotoPost =
    metadata?.videos.some((v) => v.quality === "photo") ?? false;

  const videoFormats = ["mp4", "webm", "mkv"];
  const audioFormats = ["mp3", "m4a", "opus", "flac", "ogg", "wav"];

  useEffect(() => {
    if (metadata) {
      setIsOpen(true);
      const newMode: DownloadMode =
        metadata.videos.length > 0 ? "default" : "audio_only";
      setDownloadMode(newMode);

      setSelectedVideo(metadata.videos[0]?.quality);
      setSelectedAudio(metadata.audios[0]?.quality);

      if (newMode === "audio_only") {
        setFormat("mp3");
      } else if (isPhotoPost) {
        setFormat("jpeg");
      } else {
        setFormat("mp4");
      }
    } else {
      setIsOpen(false);
    }
  }, [metadata, isPhotoPost]);

  useEffect(() => {
    if (downloadMode === "audio_only") {
      if (videoFormats.includes(format)) {
        setFormat("mp3");
      }
    } else {
      if (audioFormats.includes(format) && !["m4a"].includes(format)) {
        setFormat("mp4");
      }
    }
  }, [downloadMode, format, videoFormats, audioFormats]);

  const handleDialogClose = () => {
    if (isProcessing) return;
    setIsOpen(false);
    onOpenChange();
  };

  const handleDownload = async () => {
    if (!url || !metadata) return;
    setIsProcessing(true);

    try {
      if (isPhotoPost && thumbnailUrl) {
        const photoUrl = `${sodaliteAPI.getApiBaseUrl()}/sodalite/download/photo?url=${encodeURIComponent(
          thumbnailUrl,
        )}&format=${format}`;
        window.open(photoUrl, "_blank");
        toast.success("downloading photo!");
        handleDialogClose();
        return;
      }

      const response = await sodaliteAPI.processDownload({
        url: url,
        video_quality:
          downloadMode !== "audio_only" ? selectedVideo : undefined,
        audio_quality:
          downloadMode !== "video_only" ? selectedAudio : undefined,
        format,
        download_mode: downloadMode,
      });

      const fileName = `${metadata.title.slice(0, 40)}.${format}`;
      addTask(
        response,
        fileName,
        metadata.service,
        format,
        metadata.thumbnail_url,
      );

      toast.success("your download is on its way!");
      handleDialogClose();
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const errorMessage =
          error.response?.data?.detail?.error ||
          error.response?.data?.detail ||
          "failed to start the download.";
        toast.error(errorMessage);
      } else {
        toast.error("an unexpected error occurred.");
      }
      console.error("Error processing download:", error);
    } finally {
      setIsProcessing(false);
    }
  };

  const getAvailableFormats = () => {
    if (isPhotoPost) {
      return ["jpeg", "png"];
    }
    if (downloadMode === "audio_only") {
      return audioFormats;
    } else if (downloadMode === "video_only") {
      return videoFormats;
    } else {
      return [...videoFormats, "m4a"];
    }
  };

  const currentFormats = getAvailableFormats();

  if (!metadata) return null;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleDialogClose()}>
      <DialogContent className="max-w-[95vw] sm:max-w-2xl p-0 gap-0 overflow-hidden border-border/50 bg-card animate-pop-in mx-4">
        <VisuallyHidden>
          <DialogTitle>download options for {metadata.title}</DialogTitle>
        </VisuallyHidden>

        <button
          onClick={handleDialogClose}
          className="absolute right-3 top-3 z-50 rounded-full bg-background/50 p-1.5 hover:bg-background transition-colors"
          aria-label="close dialog"
          disabled={isProcessing}
        >
          <X className="h-4 w-4" />
        </button>

        <div className="relative h-32 sm:h-40 md:h-48 overflow-hidden bg-muted">
          {metadata.thumbnail_url ? (
            <>
              <Image
                src={metadata.thumbnail_url}
                alt={metadata.title}
                fill
                className="object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-card via-card/80 to-transparent" />
            </>
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-muted">
              <Video className="w-12 h-12 text-muted-foreground" />
            </div>
          )}

          <div className="absolute bottom-0 left-0 right-0 p-3 sm:p-4 md:p-6">
            <h2 className="text-base sm:text-lg md:text-xl font-serif font-semibold mb-1 line-clamp-2">
              {metadata.title}
            </h2>
            <p className="text-xs sm:text-sm text-muted-foreground">
              {metadata.author} • {metadata.service}
            </p>
          </div>
        </div>

        <div className="p-3 sm:p-4 md:p-6 space-y-4">
          {isPhotoPost ? (
            <div className="space-y-2">
              <label className="text-sm font-medium">download photo</label>
              <p className="text-xs text-muted-foreground">
                this is a photo post. you can download the image directly.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              <label className="text-sm font-medium">download type</label>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <button
                  disabled={isProcessing || metadata.videos.length === 0}
                  onClick={() => setDownloadMode("default")}
                  className={`flex items-center justify-center gap-2 sm:flex-col sm:gap-1 p-3 sm:p-2 rounded-md border text-sm sm:text-xs transition-all ${
                    downloadMode === "default"
                      ? "border-primary bg-primary/10"
                      : "border-border hover:border-muted-foreground"
                  }`}
                >
                  <Film className="h-4 w-4" /> video
                </button>
                <button
                  disabled={isProcessing || metadata.videos.length === 0}
                  onClick={() => setDownloadMode("video_only")}
                  className={`flex items-center justify-center gap-2 sm:flex-col sm:gap-1 p-3 sm:p-2 rounded-md border text-sm sm:text-xs transition-all ${
                    downloadMode === "video_only"
                      ? "border-primary bg-primary/10"
                      : "border-border hover:border-muted-foreground"
                  }`}
                >
                  <VolumeX className="h-4 w-4" /> muted
                </button>
                <button
                  disabled={isProcessing || metadata.audios.length === 0}
                  onClick={() => setDownloadMode("audio_only")}
                  className={`flex items-center justify-center gap-2 sm:flex-col sm:gap-1 p-3 sm:p-2 rounded-md border text-sm sm:text-xs transition-all ${
                    downloadMode === "audio_only"
                      ? "border-primary bg-primary/10"
                      : "border-border hover:border-muted-foreground"
                  }`}
                >
                  <Music className="h-4 w-4" /> audio
                </button>
              </div>
            </div>
          )}

          {!isPhotoPost && (
            <div className="space-y-4 sm:grid sm:grid-cols-2 sm:gap-4 sm:space-y-0">
              <div
                className={`space-y-2 transition-opacity ${
                  downloadMode === "audio_only" ? "opacity-40" : "opacity-100"
                }`}
              >
                <label className="flex items-center gap-2 text-sm font-medium">
                  <FileVideo className="h-4 w-4 text-muted-foreground" />
                  video quality
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {metadata.videos.slice(0, 4).map((video) => (
                    <button
                      key={video.quality}
                      onClick={() => setSelectedVideo(video.quality)}
                      disabled={isProcessing || downloadMode === "audio_only"}
                      className={`px-3 py-2.5 sm:px-2 sm:py-2 rounded-md border text-sm sm:text-xs text-center transition-all ${
                        selectedVideo === video.quality
                          ? "border-primary bg-primary/10 text-foreground"
                          : "border-border hover:border-muted-foreground"
                      }`}
                    >
                      {video.quality}
                    </button>
                  ))}
                </div>
              </div>

              <div
                className={`space-y-2 transition-opacity ${
                  downloadMode === "video_only" ? "opacity-40" : "opacity-100"
                }`}
              >
                <label className="flex items-center gap-2 text-sm font-medium">
                  <FileAudio className="h-4 w-4 text-muted-foreground" />
                  audio quality
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {metadata.audios.slice(0, 4).map((audio) => (
                    <button
                      key={audio.quality}
                      onClick={() => setSelectedAudio(audio.quality)}
                      disabled={isProcessing || downloadMode === "video_only"}
                      className={`px-3 py-2.5 sm:px-2 sm:py-2 rounded-md border text-sm sm:text-xs text-center transition-all ${
                        selectedAudio === audio.quality
                          ? "border-primary bg-primary/10 text-foreground"
                          : "border-border hover:border-muted-foreground"
                      }`}
                    >
                      {audio.quality}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          <div className="space-y-2">
            <label className="text-sm font-medium">format</label>
            <div className="flex gap-2 flex-wrap">
              {currentFormats.map((fmt) => (
                <button
                  key={fmt}
                  onClick={() => !isProcessing && setFormat(fmt)}
                  disabled={isProcessing}
                  className={`px-4 py-2 sm:px-3 sm:py-1.5 rounded-md text-sm sm:text-xs font-medium transition-all ${
                    format === fmt
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary hover:bg-secondary/80"
                  }`}
                >
                  {fmt}
                </button>
              ))}
            </div>
          </div>

          <Button
            className="w-full h-12 sm:h-11 text-base rounded-lg"
            onClick={handleDownload}
            disabled={
              isProcessing ||
              (!isPhotoPost &&
                ((downloadMode !== "audio_only" && !selectedVideo) ||
                  (downloadMode !== "video_only" && !selectedAudio)))
            }
          >
            {isProcessing ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                processing...
              </>
            ) : isPhotoPost ? (
              <>
                <ImageIcon className="mr-2 h-4 w-4" />
                download photo
              </>
            ) : (
              <>
                <Download className="mr-2 h-4 w-4" />
                download
              </>
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
