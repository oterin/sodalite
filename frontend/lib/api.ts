import axios from "axios";

const API_BASE_URL = "http://oter.hackclub.app:1337"; // Use relative paths for Vercel deployment

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

export interface ErrorDetail {
  error: string;
  service?: string;
}

export const sodaliteAPI = {
  getDownloadInfo: async (url: string): Promise<DownloadMetadata> => {
    const response = await api.post("/api/download", { url });
    return response.data;
  },

  processDownload: async (
    request: ProcessRequest,
  ): Promise<ProcessResponse> => {
    const response = await api.post("/api/process", request);
    return response.data;
  },

  getTaskStatus: async (taskId: string): Promise<ProcessResponse> => {
    const response = await api.get(`/api/task/${taskId}`);
    return response.data;
  },

  getDownloadUrl: (taskId: string): string => {
    // Use API_BASE_URL for absolute URL
    return `${API_BASE_URL}/api/download/${taskId}/file`;
  },
};
