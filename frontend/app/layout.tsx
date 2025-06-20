import type { Metadata } from "next";
import { Inter, Lora } from "next/font/google";
import { Toaster } from "sonner";
import { DownloadProvider } from "@/context/DownloadContext";
import { HealthCheckProvider } from "@/context/HealthCheckContext";
import { DownloadManager } from "@/components/download-manager";

import { HealthIndicator } from "@/components/health-indicator";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

const lora = Lora({
  weight: ["400", "500", "600", "700"],
  subsets: ["latin"],
  variable: "--font-serif",
});

export const metadata: Metadata = {
  title: "Sodalite - A friendly media downloader",
  description: "A simple, friendly downloader for your favorite platforms.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" style={{ colorScheme: "dark" }}>
      <body
        className={`${inter.variable} ${lora.variable} font-sans antialiased overflow-y-hidden`}
      >
        <HealthCheckProvider>
          <DownloadProvider>
            <div className="flex min-h-screen flex-col">
              <main className="flex-1 relative z-10">{children}</main>
            </div>
            <DownloadManager />
            <HealthIndicator />
            <Toaster
              position="bottom-center"
              theme="dark"
              richColors
              expand={false}
              toastOptions={{
                className:
                  "font-serif text-sm border-border/50 bg-card/95 backdrop-blur-sm",
              }}
            />
          </DownloadProvider>
        </HealthCheckProvider>
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50">
          <div className="flex items-center gap-4 px-3 py-1.5 bg-card/80 backdrop-blur-sm border border-border/50 rounded-full shadow-sm">
            <GitInfo />
            <HealthIndicator />
          </div>
        </div>
      </body>
    </html>
  );
}
