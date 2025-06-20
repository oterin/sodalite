"use client";

import { useState, useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import Image from "next/image";
import { useDownloads, type Task } from "@/context/DownloadContext";
import { useHealthCheck } from "@/context/HealthCheckContext";
import { Button } from "@/components/ui/button";
import {
  Download,
  CheckCircle,
  XCircle,
  Loader2,
  Trash2,
  Package,
  Music,
  Film,
  X,
  FileDown,
  Server,
  Wrench,
  Sparkles,
  Link,
  HardDrive,
  Video,
  AudioWaveform,
} from "lucide-react";
import { sodaliteAPI } from "@/lib/api";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

// a pretty, minimalistic, tree-style progress indicator
const TreeProgressIndicator = ({ phase }: { phase: Task["phase"] }) => {
  const phaseMap = {
    initializing: {
      icon: <Loader2 className="h-3 w-3 animate-spin" />,
      text: "initializing...",
      color: "text-muted-foreground",
    },
    downloading: {
      icon: <FileDown className="h-3 w-3" />,
      text: "downloading...",
      color: "text-amber-700 dark:text-amber-500",
    },
    processing: {
      icon: <Wrench className="h-3 w-3" />,
      text: "processing...",
      color: "text-brown-600 dark:text-brown-400",
    },
    completed: {
      icon: <Sparkles className="h-3 w-3" />,
      text: "completed!",
      color: "text-green-600 dark:text-green-500",
    },
    failed: {
      icon: <XCircle className="h-3 w-3" />,
      text: "failed",
      color: "text-destructive",
    },
    unknown: {
      icon: <Server className="h-3 w-3" />,
      text: "unknown",
      color: "text-muted-foreground",
    },
  };

  const currentPhase = phaseMap[phase] || phaseMap.unknown;

  return (
    <div className={cn("flex items-center gap-2", currentPhase.color)}>
      <div className="flex-none">{currentPhase.icon}</div>
      <span className="text-xs font-medium">{currentPhase.text}</span>
    </div>
  );
};

// individual download item component
const DownloadItem = ({ task }: { task: Task }) => {
  const { clearTask } = useDownloads();

  const handleDownload = () => {
    if (task.download_url) {
      window.open(sodaliteAPI.getDownloadUrl(task.task_id), "_blank");
    }
  };

  const handleCopyLink = () => {
    if (task.download_url) {
      const url = sodaliteAPI.getDownloadUrl(task.task_id);
      navigator.clipboard.writeText(url);
      toast.success("download link copied to clipboard!");
    }
  };

  const isAudioOnly = !task.video_quality && task.audio_quality;

  return (
    <div className="flex flex-col gap-2 p-3 rounded-lg hover:bg-muted/30 transition-colors group">
      <div className="flex items-center gap-3">
        <div className="shrink-0 w-10 h-10 rounded-md bg-muted overflow-hidden flex items-center justify-center">
          {task.thumbnail_url ? (
            <Image
              src={task.thumbnail_url}
              alt="thumbnail"
              width={40}
              height={40}
              className="object-cover w-full h-full"
            />
          ) : isAudioOnly ? (
            <Music className="h-5 w-5 text-muted-foreground" />
          ) : (
            <Film className="h-5 w-5 text-muted-foreground" />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <p
            className="text-sm font-medium truncate pr-2"
            title={task.fileName}
          >
            {task.fileName}
          </p>
          <div className="flex items-center gap-2 text-muted-foreground text-xs">
            {task.status === "processing" ? (
              <TreeProgressIndicator phase={task.phase} />
            ) : task.status === "failed" ? (
              <p
                className="text-xs text-destructive truncate"
                title={task.error}
              >
                {task.error || "failed"}
              </p>
            ) : (
              <div className="flex items-center gap-2">
                <CheckCircle className="h-3 w-3 text-green-500" />
                <span className="text-xs text-green-600">completed</span>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between pl-13">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="font-mono bg-secondary px-1.5 py-0.5 rounded-sm">
            {task.format.toUpperCase()}
          </span>
          {task.file_size_mb && (
            <div className="flex items-center gap-1">
              <HardDrive className="h-3 w-3" />
              <span>{task.file_size_mb.toFixed(2)} MB</span>
            </div>
          )}
          {task.video_quality && (
            <div className="flex items-center gap-1">
              <Video className="h-3 w-3" />
              <span>{task.video_quality}</span>
            </div>
          )}
          {task.audio_quality && (
            <div className="flex items-center gap-1">
              <AudioWaveform className="h-3 w-3" />
              <span>{task.audio_quality}</span>
            </div>
          )}
        </div>
        <div className="flex items-center gap-1">
          {task.status === "completed" && (
            <>
              <Button
                size="icon"
                variant="ghost"
                onClick={handleDownload}
                className="h-7 w-7"
                title="download file"
              >
                <Download className="h-3.5 w-3.5" />
              </Button>
              <Button
                size="icon"
                variant="ghost"
                onClick={handleCopyLink}
                className="h-7 w-7"
                title="copy link"
              >
                <Link className="h-3.5 w-3.5" />
              </Button>
            </>
          )}
          <Button
            size="icon"
            variant="ghost"
            onClick={() => clearTask(task.task_id)}
            className="h-7 w-7 hover:text-destructive"
            title="remove from list"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
    </div>
  );
};

// main download manager component
export function DownloadManager() {
  const { tasks, clearAllTasks } = useDownloads();
  const { isServerOnline } = useHealthCheck();
  const [isExpanded, setIsExpanded] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const prevTaskCount = useRef(tasks.length);

  useEffect(() => {
    // auto-expand when a new task is added
    if (tasks.length > prevTaskCount.current) {
      setIsExpanded(true);
    }
    prevTaskCount.current = tasks.length;
  }, [tasks]);

  // handle clicks outside to close the manager
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsExpanded(false);
      }
    };
    if (isExpanded) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isExpanded]);

  if (!isServerOnline) return null;

  const activeTasks = tasks.filter((t) => t.status === "processing");
  const completedOrFailedTasks = tasks.filter(
    (t) => t.status === "completed" || t.status === "failed",
  );

  return (
    <div className="fixed bottom-4 right-4 z-40 select-none" ref={containerRef}>
      <div className="relative">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className={cn(
            "relative w-12 h-12 rounded-full border-2 transition-all duration-300",
            "bg-card/90 backdrop-blur-sm border-border/50 shadow-lg hover:shadow-xl",
            "flex items-center justify-center",
            isExpanded && "bg-primary/10 border-primary/30",
          )}
        >
          <div className="relative flex items-center justify-center">
            {activeTasks.length > 0 ? (
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
            ) : (
              <Package className="h-5 w-5 text-muted-foreground" />
            )}
          </div>
        </button>

        {tasks.length > 0 && (
          <span className="absolute -top-1 -right-1 bg-primary text-primary-foreground text-xs rounded-full h-5 w-5 flex items-center justify-center font-mono">
            {tasks.length > 9 ? "9+" : tasks.length}
          </span>
        )}

        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              transition={{ duration: 0.15, ease: "easeOut" }}
              className="absolute bottom-16 right-0 w-[450px] bg-card/95 backdrop-blur-sm border border-border/50 rounded-lg shadow-xl"
            >
              <div className="flex items-center justify-between p-3 border-b border-border/30">
                <div className="flex items-center gap-2">
                  <Package className="h-4 w-4 text-primary" />
                  <span className="text-sm font-medium">Downloads</span>
                  {activeTasks.length > 0 && (
                    <span className="text-xs text-muted-foreground">
                      ({activeTasks.length} active)
                    </span>
                  )}
                </div>
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() => setIsExpanded(false)}
                  className="h-6 w-6"
                >
                  <X className="h-3.5 w-3.5" />
                </Button>
              </div>

              <div className="max-h-80 overflow-y-auto">
                {tasks.length === 0 ? (
                  <div className="p-8 text-center text-muted-foreground">
                    <Package className="h-10 w-10 mx-auto mb-3 opacity-50" />
                    <p className="text-sm">no downloads yet</p>
                    <p className="text-xs opacity-70">
                      downloads will appear here
                    </p>
                  </div>
                ) : (
                  <div className="p-1">
                    {tasks.map((task) => (
                      <DownloadItem key={task.task_id} task={task} />
                    ))}
                  </div>
                )}
              </div>

              {completedOrFailedTasks.length > 0 && (
                <div className="border-t border-border/30 p-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full h-7 text-xs"
                    onClick={clearAllTasks}
                  >
                    clear completed ({completedOrFailedTasks.length})
                  </Button>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
