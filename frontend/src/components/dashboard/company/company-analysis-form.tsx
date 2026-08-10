"use client";

import { useState } from "react";
import { Search, Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useAnalyzeCompany } from "@/hooks/use-company";

const formSchema = z.object({
  website_url: z.string().url("Please enter a valid URL (e.g., https://example.com)"),
});

export function CompanyAnalysisForm({ onSuccess }: { onSuccess?: (id: string) => void }) {
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const analyzeCompany = useAnalyzeCompany();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<z.infer<typeof formSchema>>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(formSchema as any),
    defaultValues: {
      website_url: "",
    },
  });

  const onSubmit = async (values: z.infer<typeof formSchema>) => {
    setSuccessMessage(null);
    try {
      const response = await analyzeCompany.mutateAsync({
        website_url: values.website_url,
        run_in_background: true,
      });
      
      setSuccessMessage("Analysis started! We will crawl the website and generate insights.");
      reset();
      
      // If the backend returns a tracking ID (either from data or a task), we might pass it back.
      // Usually the data is returned even if queued (with status="queued")
      if (onSuccess && response.data?.id) {
        onSuccess(response.data.id);
      }
    } catch {
      // Handled by the mutation state
    }
  };

  return (
    <Card className="bg-zinc-900 border-zinc-800">
      <CardHeader>
        <CardTitle className="text-lg text-white">Analyze Company</CardTitle>
        <CardDescription className="text-zinc-400">
          Enter a company&apos;s website URL to extract intelligence, products, tech stack, and generate a summary using AI.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {successMessage && (
            <div className="rounded-md border border-green-500/20 bg-green-500/10 p-3 text-sm text-green-400">
              {successMessage}
            </div>
          )}
          {analyzeCompany.isError && (
            <div className="rounded-md border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-400">
              Failed to start analysis. Please check the URL and try again.
            </div>
          )}

          <div className="flex gap-3">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
              <Input
                placeholder="https://example.com"
                {...register("website_url")}
                className="pl-9 bg-zinc-950 border-zinc-800 text-white placeholder:text-zinc-600 focus-visible:ring-zinc-700 h-10"
              />
            </div>
            <Button
              type="submit"
              disabled={analyzeCompany.isPending}
              className="bg-white text-black hover:bg-zinc-200 h-10 px-6"
            >
              {analyzeCompany.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Analyzing...
                </>
              ) : (
                "Analyze"
              )}
            </Button>
          </div>
          {errors.website_url && (
            <p className="text-sm text-red-400 mt-1">{errors.website_url.message}</p>
          )}
        </form>
      </CardContent>
    </Card>
  );
}
