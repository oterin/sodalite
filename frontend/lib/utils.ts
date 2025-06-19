import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function detectService(url: string): string {
  if (
    url.includes("instagram.com/reel") ||
    url.includes("instagram.com/reels")
  ) {
    return "Instagram Reels";
  }
  if (url.includes("youtube.com") || url.includes("youtu.be")) {
    return "YouTube";
  }
  if (url.includes("tiktok.com")) {
    return "TikTok";
  }
  return "";
}
