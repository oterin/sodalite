"use client";

import { useState, useEffect, useRef } from "react";
import {
  Megaphone,
  X,
  AlertTriangle,
  Wrench,
  Info,
  CheckCircle,
  ChevronDown,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";

interface NewsItem {
  id: string;
  type: string;
  severity: "low" | "medium" | "high" | "critical";
  title: string;
  message: string;
  timestamp: string;
  expires: string;
  show_when_offline: boolean;
  icon: string;
  color: string;
}

interface NewsData {
  version: string;
  last_updated: string;
  news: NewsItem[];
}

const iconMap = {
  "alert-triangle": AlertTriangle,
  wrench: Wrench,
  info: Info,
  megaphone: Megaphone,
  "check-circle": CheckCircle,
  "x-circle": X,
};

const colorClasses = {
  primary: "text-primary border-primary/20 bg-primary/5",
  secondary: "text-secondary-foreground border-border/30 bg-secondary/10",
  destructive: "text-destructive border-destructive/20 bg-destructive/5",
  warning:
    "text-yellow-600 dark:text-yellow-400 border-yellow-500/20 bg-yellow-500/5",
  success:
    "text-green-600 dark:text-green-500 border-green-500/20 bg-green-500/5",
};

interface NewsBannerProps {
  isServerOnline?: boolean;
}

export function NewsBanner({ isServerOnline = true }: NewsBannerProps) {
  const [newsData, setNewsData] = useState<NewsData | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchNews = async () => {
      try {
        const response = await fetch(
          "https://raw.githack.com/oterin/sodalite/main/ui_updates.json",
          {
            method: "GET",
            mode: "cors",
            cache: "no-cache",
            headers: { Accept: "application/json" },
          },
        );
        if (response.ok) {
          setNewsData(await response.json());
        }
      } catch (error) {
        console.error("Failed to fetch news:", error);
      }
    };

    fetchNews();
    const interval = setInterval(fetchNews, 5 * 60 * 1000); // refetch every 5 mins
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsExpanded(false);
      }
    };
    if (isExpanded) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isExpanded]);

  if (!newsData) {
    return null;
  }

  const activeNews = newsData.news
    .filter((item) => {
      const expires = new Date(item.expires);
      const shouldShow = isServerOnline || item.show_when_offline;
      return expires > new Date() && shouldShow;
    })
    .sort(
      (a, b) =>
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
    );

  if (activeNews.length === 0) {
    return null;
  }

  const mostRecentItem = activeNews[0];
  const IconComponent =
    iconMap[mostRecentItem.icon as keyof typeof iconMap] || Info;
  const colorClass =
    colorClasses[mostRecentItem.color as keyof typeof colorClasses] ||
    colorClasses.secondary;

  return (
    <div className="w-full" ref={containerRef}>
      <motion.div layout className={cn("rounded-lg border", colorClass)}>
        <div
          className="flex items-center gap-3 p-3 cursor-pointer"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <IconComponent className="h-4 w-4 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">
              {mostRecentItem.title}
            </p>
          </div>
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <span>
              {activeNews.length > 1 ? `1 of ${activeNews.length}` : "details"}
            </span>
            <motion.div
              animate={{ rotate: isExpanded ? 180 : 0 }}
              transition={{ duration: 0.2 }}
            >
              <ChevronDown className="h-4 w-4" />
            </motion.div>
          </div>
        </div>

        <AnimatePresence>
          {isExpanded && (
            <motion.div
              key="news-content"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2, ease: "easeInOut" }}
              className="overflow-hidden"
            >
              <div className="border-t border-[color:inherit] opacity-30 mx-3"></div>
              <div className="px-3 pt-2 pb-3 space-y-3">
                {activeNews.map((item, index) => (
                  <div key={item.id}>
                    {index > 0 && (
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="text-sm font-medium">{item.title}</h3>
                      </div>
                    )}
                    <p className="text-xs leading-relaxed text-muted-foreground">
                      {item.message}
                    </p>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
