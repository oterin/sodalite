"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { Download, Loader2 } from "lucide-react";
import { detectService } from "@/lib/utils";

const formSchema = z.object({
  url: z.string().url("Please enter a valid URL").min(1, "URL is required"),
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
  if (urlValue && detectService(urlValue) !== detectedService) {
    setDetectedService(detectService(urlValue));
  }

  const onFormSubmit = async (data: FormData) => {
    await onSubmit(data.url);
  };

  return (
    <Card className="p-6">
      <form onSubmit={handleSubmit(onFormSubmit)} className="space-y-4">
        <div className="space-y-2">
          <Input
            {...register("url")}
            placeholder="Paste your link here..."
            className="text-lg h-12"
            disabled={isLoading}
            autoComplete="off"
          />
          {errors.url && (
            <p className="text-sm text-destructive">{errors.url.message}</p>
          )}
          {detectedService && (
            <p className="text-sm text-muted-foreground">
              Detected: {detectedService}
            </p>
          )}
        </div>
        <Button
          type="submit"
          className="w-full h-12 text-lg"
          disabled={isLoading}
        >
          {isLoading ? (
            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
          ) : (
            <Download className="mr-2 h-5 w-5" />
          )}
          {isLoading ? "Fetching..." : "Get Download Options"}
        </Button>
      </form>
    </Card>
  );
}
