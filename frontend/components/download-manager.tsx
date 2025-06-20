"use client";

import { useState, useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import Image from "next/image";
import { useDownloads, type Task } from "@/context/DownloadContext";
import { useHealthCheck } from "@/context/HealthCheckContext";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
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
} from "lucide-react";
import { sodaliteAPI } from "@/lib/api";
import { cn } from "@/lib/utils";

const DownloadItem = ({ task }: { task: Task }) => {
  const { clearTask } = useDownloads();

  const handleDownload = () => {
    if (task.download_url) {
      window.open(sodaliteAPI.getDownloadUrl(task.task_id), "_blank");
    }
  };

  const getStatusIcon = () => {
    switch (task.status) {
      case "processing":
        return <Loader2 className="h-3 w-3 animate-spin text-primary" />;
      case "completed":
        return <CheckCircle className="h-3 w-3 text-green-500" />;
      case "failed":
        return <XCircle className="h-3 w-3 text-destructive" />;
    }
  };

  const isAudio = ["mp3", "m4a", "wav", "flac", "opus"].includes(task.format);

  return (
    <div className="flex items-center gap-2 p-2 rounded-md hover:bg-muted/30 transition-colors group">
      {/* thumbnail */}
      <div className="shrink-0 w-6 h-6 rounded bg-muted overflow-hidden flex items-center justify-center">
        {task.thumbnail_url ? (
          <Image
            src={task.thumbnail_url}
            alt="thumbnail"
            width={24}
            height={24}
            className="object-cover w-full h-full"
          />
        ) : isAudio ? (
          <Music className="h-3 w-3 text-muted-foreground" />
        ) : (
          <Film className="h-3 w-3 text-muted-foreground" />
        )}
      </div>

      {/* content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1">
          <p
            className="text-xs font-medium truncate pr-2"
            title={task.fileName}
          >
            {task.fileName.length > 25
              ? `${task.fileName.slice(0, 25)}...`
              : task.fileName}
          </p>
          <div className="flex items-center gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
            {getStatusIcon()}
            {task.status === "completed" && (
              <Button
                size="icon"
                variant="ghost"
                onClick={handleDownload}
                className="h-5 w-5"
              >
                <Download className="h-2.5 w-2.5" />
              </Button>
            )}
            <Button
              size="icon"
              variant="ghost"
              onClick={() => clearTask(task.task_id)}
              className="h-5 w-5 hover:text-destructive"
            >
              <Trash2 className="h-2.5 w-2.5" />
            </Button>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground font-mono">
            {task.format.toUpperCase()}
          </span>
          {task.status === "processing" && (
            <>
              <Progress value={task.progress} className="h-1 flex-1" />
              <span className="text-xs text-muted-foreground">
                {Math.round(task.progress)}%
              </span>
            </>
          )}
          {task.status === "completed" && (
            <span className="text-xs text-green-600">completed</span>
          )}
          {task.status === "failed" && (
            <span className="text-xs text-destructive">failed</span>
          )}
        </div>
      </div>
    </div>
  );
};

export function DownloadManager() {
  const { tasks, clearAllTasks } = useDownloads();
  const { isServerOnline } = useHealthCheck();
  const [isExpanded, setIsExpanded] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // don't show if server is offline
  if (!isServerOnline) return null;

  // auto-expand when new download starts
  useEffect(() => {
    const hasProcessingTasks = tasks.some(
      (task) => task.status === "processing",
    );
    if (hasProcessingTasks && !isExpanded) {
      setIsExpanded(true);
    }
  }, [tasks, isExpanded]);

  // click outside to close
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node) &&
        isExpanded
      ) {
        setIsExpanded(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isExpanded]);

  const activeTasks = tasks.filter((t) => t.status === "processing");
  const completedTasks = tasks.filter((t) => t.status === "completed");
  const totalProgress =
    activeTasks.length > 0
      ? activeTasks.reduce((sum, task) => sum + task.progress, 0) /
        activeTasks.length
      : 0;

  return (
    <div className="fixed bottom-4 right-4 z-40 select-none" ref={containerRef}>
      {/* always visible circular button */}
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
          {/* progress ring for active downloads */}
          {activeTasks.length > 0 && (
            <svg className="absolute inset-0 w-12 h-12 -rotate-90">
              <circle
                cx="24"
                cy="24"
                r="20"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                className="text-muted/30"
              />
              <circle
                cx="24"
                cy="24"
                r="20"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeDasharray={`${2 * Math.PI * 20}`}
                strokeDashoffset={`${2 * Math.PI * 20 * (1 - totalProgress / 100)}`}
                className="text-primary transition-all duration-500"
                strokeLinecap="round"
              />
            </svg>
          )}

          {/* icon and count */}
          <div className="relative flex items-center justify-center">
            {activeTasks.length > 0 ? (
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
            ) : (
              <Package className="h-4 w-4 text-muted-foreground" />
            )}
          </div>
        </button>

        {/* count badge positioned at top-right of the button */}
        {tasks.length > 0 && (
          <span className="absolute -top-1 -right-1 bg-primary text-primary-foreground text-xs rounded-full h-5 w-5 flex items-center justify-center font-mono">
            {tasks.length > 9 ? "9+" : tasks.length}
          </span>
        )}

        {/* expandable panel */}
        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ opacity: 0, scale: 0.98, y: 4 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.98, y: 4 }}
              transition={{ duration: 0.12, ease: "easeOut" }}
              className="absolute bottom-16 right-0 w-80 bg-card/95 backdrop-blur-sm border border-border/50 rounded-lg shadow-xl"
            >
              {/* header */}
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

              {/* content */}
              <div className="max-h-64 overflow-y-auto">
                {tasks.length === 0 ? (
                  <div className="p-6 text-center text-muted-foreground">
                    <Package className="h-8 w-8 mx-auto mb-2 opacity-50" />
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

              {/* footer */}
              {completedTasks.length > 0 && (
                <div className="border-t border-border/30 p-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full h-7 text-xs"
                    onClick={clearAllTasks}
                  >
                    clear completed ({completedTasks.length})
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
