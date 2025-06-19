"use client";

import { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Download, Video, Music } from "lucide-react";
import {
  sodaliteAPI,
  type DownloadMetadata,
  type ProcessResponse,
} from "@/lib/api";
import { toast } from "sonner";

interface QualitySelectorProps {
  metadata: DownloadMetadata;
  onTaskCreated: (task: ProcessResponse) => void;
}

export function QualitySelector({ metadata, onTaskCreated }: QualitySelectorProps) {
  const [selectedVideo, setSelectedVideo] = useState<string | undefined>(
    metadata.videos[0]?.quality
  );
  const [selectedAudio, setSelectedAudio] = useState<string | undefined>(
    metadata.audios[0]?.quality
  );
  const [format, setFormat] = useState<"mp4" | "webm" | "mkv">("mp4");
  const [isProcessing, setIsProcessing] = useState(false);

  const handleDownload = async () => {
    setIsProcessing(true);

    try {
      const response = await sodaliteAPI.processDownload({
        url: window.location.href, // we lowk need the original url
        video_quality: selectedVideo,
        audio_quality: selectedAudio,
        format,
      });

      onTaskCreated(response);
      toast.success("Procesing started! Your download will be ready soon.");
    } catch (error: any) {
      const errorMessage =
        error.response?.data?.detail?.error || "Failed to start download";
      toast.error(errorMessage);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="line-clamp-1">{metadata.title}</CardTitle>
        <CardDescription>by {metadata.author} • {metadata.service}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {metadata.videos.length > 0 && (
          <div className="space-y-2">
            <Label className="flex items-center gap-2">
              <Video className="h-4 w-4" />
              Video Quality
            </Label>
            <Select value={selectedVideo} onValueChange={setSelectedVideo}>
              <SelectTrigger>
                <SelectValue placeholder="Select video quality" />
              </SelectTrigger>
              <SelectContent>
                {metadata.videos.map((video, index) => (
                  <SelectItem key={index} value={video.quality}>
                    {video.quality}
                    {video.width && video.height && (
                      <span className="text-muted-foreground ml-2">
                        ({video.width}×{video.height})
                      </span>
                    )}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}

        {metadata.audios.length > 0 && (
          <div className="space-y-2">
            <Label className="flex items-center gap-2">
              <Music className="h-4 w-4" />
              Audio Quality
            </Label>
            <Select value={selectedAudio} onValueChange={setSelectedAudio}>
              <SelectTrigger>
                <SelectValue placeholder="Select audio quality" />
              </SelectTrigger>
              <SelectContent>
                {metadata.audios.map((audio, index) => (
                  <SelectItem key={index} value={audio.quality}>
                    {audio.quality}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}

        <div className="space-y-2">
          <Label>Format</Label>
          <div className="flex gap-2">
            {(["mp4", "webm", "mkv"] as const).map((fmt) => (
              <Badge
                key={fmt}
                variant={format === fmt ? "default" : "secondary"}
                className="cursor-pointer"
                onClick={() => setFormat(fmt)}
              >
                {fmt.toUpperCase()}
              </Badge>
            ))}
          </div>
        </div>

        <Button className="w-full" onClick={handleDownload} disabled={isProcessing}>
          <Download className="mr-2 h-4 w-4" />
          {isProcessing ? "Processing..." : "Download"}
        </Button>
      </CardContent>
    </Card>
  );
