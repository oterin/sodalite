import { GitBranch } from 'lucide-react';

function timeAgo(timestamp: number): string {
  const now = Date.now();
  const seconds = Math.floor((now - timestamp) / 1000);

  if (seconds < 60) return `${seconds}s ago`;

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function GitInfo() {
  const commitRef = process.env.VERCEL_GIT_COMMIT_REF;
  const commitSha = process.env.VERCEL_GIT_COMMIT_SHA;
  const commitTimestamp = process.env.VERCEL_GIT_COMMIT_TIMESTAMP;

  // These variables are only available on Vercel deployments
  if (!commitRef || !commitSha || !commitTimestamp) {
    return null;
  }

  const shortSha = commitSha.slice(0, 7);
  const commitTime = timeAgo(Number(commitTimestamp) * 1000);
  const githubUrl = `https://github.com/oterin/sodalite/commit/${commitSha}`;

  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50">
      <a
        href={githubUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors px-3 py-1.5 bg-card/80 backdrop-blur-sm border border-border/50 rounded-full shadow-sm"
      >
        <GitBranch className="h-3.5 w-3.5" />
        <span>
          {commitRef} ({shortSha}) &ndash; {commitTime}
        </span>
      </a>
    </div>
  );
}
