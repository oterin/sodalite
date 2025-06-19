"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import { type ProcessResponse, sodaliteAPI } from "@/lib/api";

export interface Task extends ProcessResponse {
  fileName: string;
  progress: number;
  service: string;
  format: string;
  thumbnail_url?: string;
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

  useEffect(() => {
    const progressInterval = setInterval(() => {
      setTasks((currentTasks) =>
        currentTasks.map((task) => {
          if (task.status === "processing" && task.progress < 90) {
            const increment = Math.random() * 3;
            return {
              ...task,
              progress: Math.min(task.progress + increment, 90),
            };
          }
          return task;
        }),
      );
    }, 800);

    const statusInterval = setInterval(() => {
      tasks.forEach((task) => {
        if (task.status === "processing") {
          sodaliteAPI.getTaskStatus(task.task_id).then((updatedTask) => {
            if (updatedTask.status !== "processing") {
              setTasks((currentTasks) =>
                currentTasks.map((t) =>
                  t.task_id === updatedTask.task_id
                    ? {
                        ...t,
                        status: updatedTask.status,
                        download_url: updatedTask.download_url,
                        error: updatedTask.error,
                        progress:
                          updatedTask.status === "completed" ? 100 : t.progress,
                      }
                    : t,
                ),
              );
            }
          });
        }
      });
    }, 2000);

    return () => {
      clearInterval(progressInterval);
      clearInterval(statusInterval);
    };
  }, [tasks]);

  const addTask = (
    task: ProcessResponse,
    fileName: string,
    service: string,
    format: string,
    thumbnail_url?: string,
  ) => {
    const newTask: Task = {
      ...task,
      fileName,
      progress: 0,
      service,
      format,
      thumbnail_url,
    };
    setTasks((prev) => [newTask, ...prev]);
  };

  const clearTask = (taskId: string) => {
    setTasks((prev) => prev.filter((task) => task.task_id !== taskId));
  };

  const clearAllTasks = () => {
    setTasks(tasks.filter((task) => task.status === "processing"));
  };

  return (
    <DownloadContext.Provider
      value={{ tasks, addTask, clearTask, clearAllTasks }}
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
