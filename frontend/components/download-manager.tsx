"use client";

import { useState } from "react";
import Image from "next/image";
import { useDownloads, type Task } from "@/context/DownloadContext";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import {
  Download,
  CheckCircle,
  XCircle,
  Loader2,
  Trash2,
  ChevronDown,
  ChevronUp,
  Package,
  Music,
  Film,
} from "lucide-react";
import { sodaliteAPI } from "@/lib/api";
import { AnimatePresence, motion } from "framer-motion";
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
        return <Loader2 className="h-4 w-4 animate-spin text-primary" />;
      case "completed":
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-destructive" />;
    }
  };

  const isAudio = ["mp3", "m4a", "wav", "flac", "opus"].includes(task.format);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ type: "spring", stiffness: 300, damping: 25 }}
      className="group flex items-center gap-3 p-2 rounded-lg"
    >
      <div className="shrink-0 w-12 h-12 rounded-md bg-muted overflow-hidden flex items-center justify-center">
        {task.thumbnail_url ? (
          <Image
            src={task.thumbnail_url}
            alt="thumbnail"
            width={64}
            height={64}
            quality={100}
            className="object-cover w-full h-full"
          />
        ) : isAudio ? (
          <Music className="h-6 w-6 text-muted-foreground" />
        ) : (
          <Film className="h-6 w-6 text-muted-foreground" />
        )}
      </div>

      <div className="flex-grow min-w-0 space-y-1.5">
        <p className="truncate text-sm font-medium" title={task.fileName}>
          {task.fileName}
        </p>
        <div className="flex items-center gap-2">
          <Badge variant="secondary" className="text-xs">
            {task.format.toUpperCase()}
          </Badge>
          <Progress value={task.progress} className="h-1 flex-1" />
        </div>
      </div>
      <div className="shrink-0 flex items-center gap-1">
        {getStatusIcon()}
        <div className="opacity-0 group-hover:opacity-100 transition-opacity">
          {task.status === "completed" && (
            <Button
              size="icon"
              variant="ghost"
              onClick={handleDownload}
              className="h-7 w-7"
            >
              <Download className="h-3.5 w-3.5" />
            </Button>
          )}
          <Button
            size="icon"
            variant="ghost"
            onClick={() => clearTask(task.task_id)}
            className="h-7 w-7 hover:text-destructive"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
    </motion.div>
  );
};

export function DownloadManager() {
  const { tasks, clearAllTasks } = useDownloads();
  const [isOpen, setIsOpen] = useState(true);

  if (tasks.length === 0) return null;

  const activeTasks = tasks.filter((t) => t.status === "processing").length;
  const completedTasks = tasks.filter((t) => t.status === "completed");

  return (
    <motion.div
      initial={{ y: 100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className={cn(
        "fixed z-50",
        "bottom-4 right-4",
        "sm:bottom-6 sm:right-6",
        "w-[calc(100vw-2rem)] sm:w-[420px]",
      )}
    >
      <Card className="shadow-2xl bg-card/95 backdrop-blur-md border-border/50">
        <CardHeader
          className="p-3 cursor-pointer select-none"
          onClick={() => setIsOpen(!isOpen)}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Package className="h-5 w-5 text-primary" />
              <CardTitle className="text-base font-sans font-medium">
                Downloads
              </CardTitle>
            </div>
            <div className="flex items-center gap-2">
              <AnimatePresence>
                {activeTasks > 0 && (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    exit={{ scale: 0 }}
                  >
                    <Badge
                      variant="secondary"
                      className="text-xs h-5 pointer-events-none"
                    >
                      {activeTasks} processing
                    </Badge>
                  </motion.div>
                )}
              </AnimatePresence>
              <Button size="icon" variant="ghost" className="h-7 w-7">
                {isOpen ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronUp className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>
        </CardHeader>

        <AnimatePresence>
          {isOpen && (
            <motion.div
              key="content"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3, ease: [0.25, 1, 0.5, 1] }}
              className="overflow-hidden"
            >
              <CardContent className="p-1.5">
                <div className="max-h-[280px] overflow-y-auto space-y-1">
                  {tasks.map((task) => (
                    <DownloadItem key={task.task_id} task={task} />
                  ))}
                </div>
                {completedTasks.length > 0 && (
                  <div className="p-1 mt-1 border-t border-border/50">
                    <Button
                      variant="ghost"
                      className="w-full h-8 text-xs"
                      onClick={clearAllTasks}
                    >
                      clear completed
                    </Button>
                  </div>
                )}
              </CardContent>
            </motion.div>
          )}
        </AnimatePresence>
      </Card>
    </motion.div>
  );
}
