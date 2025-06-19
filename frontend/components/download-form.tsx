"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { Download, Loader2, Sparkles } from "lucide-react";
import { detectService } from "@/lib/utils";

const formSchema = z.object({
  url: z
    .string()
    .url("that doesn't look like a valid url.")
    .min(1, "you forgot to paste the link!"),
});

type FormData = z.infer<typeof formSchema>;

interface DownloadFormProps {
  onSubmit: (url: string) => Promise<void>;
  isLoading: boolean;
}

export function DownloadForm({ onSubmit, isLoading }: DownloadFormProps) {
  const [detectedService, setDetectedService] = useState("");

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
  } = useForm<FormData>({
    resolver: zodResolver(formSchema),
  });

  // watch url changes to detect service
  const urlValue = watch("url");
  useEffect(() => {
    const service = detectService(urlValue || "");
    if (service !== detectedService) {
      setDetectedService(service);
    }
  }, [urlValue, detectedService]);

  const onFormSubmit = async (data: FormData) => {
    await onSubmit(data.url);
  };

  return (
    <Card className="p-6 sm:p-8 bg-card/95 backdrop-blur-sm border-border/50 shadow-lg">
      <form onSubmit={handleSubmit(onFormSubmit)} className="space-y-4">
        <div className="space-y-2">
          <div className="relative">
            <Input
              {...register("url")}
              placeholder="paste a link here..."
              className="text-base h-12 px-4 rounded-lg bg-input/80 placeholder:text-muted-foreground/70 focus:bg-input"
              disabled={isLoading}
              autoComplete="off"
            />
          </div>
          {errors.url && (
            <p className="text-sm text-destructive pl-1 animate-pop-in">
              {errors.url.message}
            </p>
          )}
          {detectedService && (
            <p className="flex items-center gap-2 text-sm text-primary pl-1 animate-pop-in">
              <Sparkles className="h-4 w-4" />
              {`ooh, ${detectedService.toLowerCase()}! great choice.`}
            </p>
          )}
        </div>
        <Button
          type="submit"
          className="w-full h-11 text-base rounded-lg font-medium"
          disabled={isLoading || !watch("url")}
        >
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              looking for it...
            </>
          ) : (
            <>
              <Download className="mr-2 h-4 w-4" />
              fetch media
            </>
          )}
        </Button>
      </form>
    </Card>
  );
}
