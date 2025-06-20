"use client";

import { useState, useEffect } from "react";
import { GitBranch } from "lucide-react";
import { sodaliteAPI, type GitInfo as GitInfoType } from "@/lib/api";

function timeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (seconds < 60) return `${seconds}s ago`;

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function GitInfo() {
  const [gitInfo, setGitInfo] = useState<GitInfoType | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchGitInfo = async () => {
      try {
        const data = await sodaliteAPI.getGitInfo();
        setGitInfo(data);
      } catch (err) {
        console.error("Failed to fetch git info:", err);
        setError("Could not load git information.");
      }
    };

    fetchGitInfo();
  }, []);

  if (error || !gitInfo) {
    return null;
  }

  const shortSha = gitInfo.commit_sha.slice(0, 7);
  const commitTime = timeAgo(gitInfo.commit_date);
  const githubUrl = `https://github.com/oterin/sodalite/commit/${gitInfo.commit_sha}`;

  return (
    <div className="fixed bottom-4 left-4 z-30">
      <a
        href={githubUrl}
        target="_blank"
        rel="noopener noreferrer"
        title={gitInfo.commit_message}
        className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors px-3 py-1.5 bg-card/80 backdrop-blur-sm border border-border/50 rounded-full shadow-sm"
      >
        <GitBranch className="h-3.5 w-3.5" />
        <span>
          {gitInfo.branch} ({shortSha}) &ndash; {commitTime}
        </span>
      </a>
    </div>
  );
}
