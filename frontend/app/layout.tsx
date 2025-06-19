import type { Metadata } from "next";
import { Inter, Lora } from "next/font/google";
import { Toaster } from "sonner";
import { DownloadProvider } from "@/context/DownloadContext";
import { DownloadManager } from "@/components/download-manager";
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
        className={`${inter.variable} ${lora.variable} font-sans antialiased`}
      >
        <DownloadProvider>
          <div className="flex min-h-screen flex-col">
            <main className="flex-1 relative z-10">{children}</main>
          </div>
          <DownloadManager />
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
      </body>
    </html>
  );
}
