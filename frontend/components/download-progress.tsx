"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { CheckCircle, XCircle, Loader2, Download } from "lucide-react";
import { sodaliteAPI, type ProcessResponse } from "@/lib/api";
import { toast } from "sonner";

interface DownloadProgressProps {
  task: ProcessResponse;
}

export function DownloadProgress({ task: initialTask }: DownloadProgressProps) {
  const [task, setTask] = useState(initialTask);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (task.status === "processing") {
      const interval = setInterval(async () => {
        try {
          const updatedTask = await sodaliteAPI.getTaskStatus(task.task_id);
          setTask(updatedTask);

          if (updatedTask.status === "completed") {
            setProgress(100);
            toast.success("Download ready!");
            clearInterval(interval);
          } else if (updatedTask.status === "failed") {
            toast.error(updatedTask.error || "Download failed");
            clearInterval(interval);
          } else {
            // i'm lazy to make ts communicate with the backend so we're just gonna fake it lol
            setProgress((prev) => Math.min(prev + 10, 90));
          }
        } catch (error) {
          console.error("Failed to check task status:", error);
        }
      }, 1000);

      return () => clearInterval(interval);
    }
  }, [task]);

  const handleDownload = () => {
    if (task.download_url) {
      window.open(sodaliteAPI.getDownloadUrl(task.task_id), "_blank");
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {task.status === "processing" && (
            <Loader2 className="h-5 w-5 animate-spin" />
          )}
          {task.status === "completed" && (
            <CheckCircle className="h-5 w-5 text-green-500" />
          )}
          {task.status === "failed" && (
            <XCircle className="h-5 w-5 text-red-500" />
          )}
          {task.status === "processing" && "Processing your download..."}
          {task.status === "completed" && "Download ready!"}
          {task.status === "failed" && "Download failed"}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {task.status === "processing" && (
          <Progress value={progress} className="w-full" />
        )}

        {task.status === "completed" && (
          <Button className="w-full" onClick={handleDownload}>
            <Download className="mr-2 h-4 w-4" />
            Download File
          </Button>
        )}

        {task.status === "failed" && task.error && (
          <p className="text-sm text-muted-foreground">{task.error}</p>
        )}
      </CardContent>
    </Card>
  );
}
