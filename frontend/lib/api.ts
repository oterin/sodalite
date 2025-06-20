import axios from "axios";

const API_BASE_URL = "https://backend.otter.llc:1335";

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export interface DownloadMetadata {
  service: string;
  title: string;
  author: string;
  thumbnail_url?: string;
  videos: Array<{
    url: string;
    quality: string;
    width?: number;
    height?: number;
    headers?: Record<string, string>;
  }>;
  audios: Array<{
    url: string;
    quality: string;
    headers?: Record<string, string>;
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
  getDownloadInfo: async (url: string): Promise<DownloadMetadata> => {
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
