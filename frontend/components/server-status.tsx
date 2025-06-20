"use client";

import { ServerCrash } from "lucide-react";

export function ServerStatus() {
  return (
    <div className="container relative mx-auto flex min-h-screen flex-col items-center justify-center px-4 py-8 text-center animate-fade-in">
      <div className="w-full max-w-lg space-y-6">
        <div className="flex justify-center">
          <ServerCrash
            className="h-16 w-16 text-destructive/80"
            strokeWidth={1.5}
          />
        </div>
        <div className="space-y-3">
          <h1 className="text-4xl sm:text-5xl font-serif font-bold tracking-tight">
            sodalite is sleeping
          </h1>
          <p className="text-lg text-muted-foreground">
            it seems the server is currently offline.
            <br />
            please try again later.
          </p>
        </div>
      </div>
    </div>
  );
}
