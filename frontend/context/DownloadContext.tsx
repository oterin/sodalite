"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
  useCallback,
} from "react";
import { sodaliteAPI, type ProcessResponse } from "@/lib/api";

export interface Task extends ProcessResponse {
  fileName: string;
  phase: "initializing" | "downloading" | "processing" | "completed" | "failed";
  service: string;
  format: string;
  thumbnail_url?: string;
  file_size_mb?: number;
  video_quality?: string;
  audio_quality?: string;
}

interface DownloadContextType {
  tasks: Task[];
  addTask: (
    task: ProcessResponse,
    fileName: string,
    service: string,
    format: string,
    thumbnail_url?: string,
  ) => void;
  clearTask: (taskId: string) => void;
  clearAllTasks: () => void;
}

const DownloadContext = createContext<DownloadContextType | undefined>(
  undefined,
);

export const DownloadProvider = ({ children }: { children: ReactNode }) => {
  const [tasks, setTasks] = useState<Task[]>([]);

  // polling mechanism to update task statuses
  useEffect(() => {
    const activeTasks = tasks.filter((task) => task.status === "processing");

    if (activeTasks.length === 0) {
      return; // no need to poll if no tasks are active
    }

    const interval = setInterval(async () => {
      for (const task of activeTasks) {
        try {
          const updatedPhase = await sodaliteAPI.getTaskPhase(task.task_id);

          // update task phase if it has changed
          if (updatedPhase.phase !== task.phase) {
            setTasks((prev) =>
              prev.map((t) =>
                t.task_id === task.task_id
                  ? { ...t, phase: updatedPhase.phase }
                  : t,
              ),
            );
          }

          // if task is no longer processing, fetch final status
          if (updatedPhase.status !== "processing") {
            const finalStatus = await sodaliteAPI.getTaskStatus(task.task_id);
            setTasks((prev) =>
              prev.map((t) =>
                t.task_id === task.task_id
                  ? {
                      ...t,
                      status: finalStatus.status,
                      phase:
                        finalStatus.status === "completed"
                          ? "completed"
                          : "failed",
                      download_url: finalStatus.download_url,
                      error: finalStatus.error,
                      file_size_mb: finalStatus.file_size_mb,
                      video_quality: finalStatus.video_quality,
                      audio_quality: finalStatus.audio_quality,
                    }
                  : t,
              ),
            );
          }
        } catch (error) {
          console.error(
            `failed to update status for task ${task.task_id}:`,
            error,
          );
          // mark task as failed on network error
          setTasks((prev) =>
            prev.map((t) =>
              t.task_id === task.task_id
                ? {
                    ...t,
                    status: "failed",
                    phase: "failed",
                    error: "failed to get status update.",
                  }
                : t,
            ),
          );
        }
      }
    }, 2000); // poll every 2 seconds

    return () => clearInterval(interval);
  }, [tasks]);

  const addTask = useCallback(
    (
      task: ProcessResponse,
      fileName: string,
      service: string,
      format: string,
      thumbnail_url?: string,
    ) => {
      const newTask: Task = {
        ...task,
        fileName,
        phase: "initializing",
        service,
        format,
        thumbnail_url,
      };
      // add to the top of the list
      setTasks((prev) => [newTask, ...prev]);
    },
    [],
  );

  const clearTask = useCallback((taskId: string) => {
    setTasks((prev) => prev.filter((task) => task.task_id !== taskId));
  }, []);

  const clearAllTasks = useCallback(() => {
    // only clear completed or failed tasks
    setTasks((prev) => prev.filter((task) => task.status === "processing"));
  }, []);

  return (
    <DownloadContext.Provider
      value={{
        tasks,
        addTask,
        clearTask,
        clearAllTasks,
      }}
    >
      {children}
    </DownloadContext.Provider>
  );
};

export const useDownloads = (): DownloadContextType => {
  const context = useContext(DownloadContext);
  if (!context) {
    throw new Error("useDownloads must be used within a DownloadProvider");
  }
  return context;
};
