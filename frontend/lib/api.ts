import axios from "axios";

const API_BASE_URL = "http://localhost:1335";
const WS_BASE_URL = API_BASE_URL.replace("https://", "wss://").replace(
  "http://",
  "ws://",
);

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export const getWebSocketUrl = (path: string): string => {
  return `${WS_BASE_URL}${path}`;
};

export interface SanitizedDownloadMetadata {
  service: string;
  title: string;
  author: string;
  thumbnail_url?: string;
  videos: Array<{
    quality: string;
    width?: number;
    height?: number;
    codec?: string;
  }>;
  audios: Array<{
    quality: string;
    codec?: string;
  }>;
}

export interface ProcessRequest {
  url: string;
  video_quality?: string;
  audio_quality?: string;
  format?: string;
  download_mode?: "default" | "video_only" | "audio_only";
}

export interface ProcessResponse {
  task_id: string;
  status: "processing" | "completed" | "failed";
  download_url?: string;
  error?: string;
}

export interface TaskPhase {
  task_id: string;
  phase: "initializing" | "downloading" | "processing" | "completed" | "failed";
  status: "processing" | "completed" | "failed";
}

export interface GitInfo {
  branch: string;
  commit_sha: string;
  commit_date: string;
  commit_message: string;
}

export interface ErrorDetail {
  error: string;
  service?: string;
}

export const sodaliteAPI = {
  getDownloadInfo: async (url: string): Promise<SanitizedDownloadMetadata> => {
    const response = await api.post("/sodalite/download", { url });
    return response.data;
  },

  processDownload: async (
    request: ProcessRequest,
  ): Promise<ProcessResponse> => {
    const response = await api.post("/sodalite/process", request);
    return response.data;
  },

  getTaskStatus: async (taskId: string): Promise<ProcessResponse> => {
    const response = await api.get(`/sodalite/task/${taskId}`);
    return response.data;
  },

  getTaskPhase: async (taskId: string): Promise<TaskPhase> => {
    const response = await api.get(`/sodalite/task/${taskId}/phase`);
    return response.data;
  },

  getGitInfo: async (): Promise<GitInfo> => {
    const response = await api.get("/sodalite/git-info");
    return response.data;
  },
  getDownloadUrl: (taskId: string): string => {
    return `${API_BASE_URL}/sodalite/download/${taskId}/file`;
  },

  healthCheck: async (): Promise<{ status: string; heartbeats: number }> => {
    const response = await api.get("/sodalite/health");
    return response.data;
  },
};
