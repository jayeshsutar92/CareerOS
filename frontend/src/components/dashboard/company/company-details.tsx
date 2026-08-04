"use client";

import { Building2, Code, Globe, Loader2, Mail, RefreshCw, Briefcase, FileText, AlertTriangle } from "lucide-react";
import { format } from "date-fns";
import { useCompanyIntelligence, useRefreshCompanyIntelligence } from "@/hooks/use-company";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/dashboard/error-state";
import { EmptyState } from "@/components/dashboard/empty-state";

interface CompanyDetailsProps {
  id: string | null;
}

export function CompanyDetails({ id }: CompanyDetailsProps) {
  const { data, isLoading, isError, isRefetching } = useCompanyIntelligence(id ?? "");
  const refreshMutation = useRefreshCompanyIntelligence();

  if (!id) {
    return (
      <div className="flex items-center justify-center h-[600px] border border-zinc-800 rounded-md bg-zinc-900/50">
        <EmptyState 
          icon={Building2}
          title="No Company Selected"
          description="Select a company from the list or run a new analysis to view intelligence data, tech stack, and summaries."
        />
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex flex-col h-[600px] border border-zinc-800 rounded-md bg-zinc-900/50 p-6 space-y-6">
        <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
          <div>
            <Skeleton className="h-8 w-64 mb-2" />
            <Skeleton className="h-4 w-40" />
          </div>
          <Skeleton className="h-9 w-32" />
        </div>
        <div className="space-y-4 pt-4">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-6 w-40 mt-6" />
          <div className="flex gap-2">
            <Skeleton className="h-6 w-24" />
            <Skeleton className="h-6 w-20" />
            <Skeleton className="h-6 w-32" />
          </div>
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="flex items-center justify-center h-[600px] border border-zinc-800 rounded-md bg-zinc-900/50 p-6">
        <ErrorState 
          title="Failed to load company details"
          description="We couldn't retrieve the company's intelligence data. Please try again."
        />
      </div>
    );
  }

  const isProcessing = data.status === "queued" || data.status === "processing";

  return (
    <Card className="bg-zinc-950 border-zinc-800 flex flex-col h-[600px]">
      <CardHeader className="border-b border-zinc-800 pb-4 bg-zinc-900/50">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-2xl text-white flex items-center gap-2">
              {data.company_name}
              {isProcessing && (
                <Badge variant="outline" className="bg-yellow-500/10 text-yellow-500 border-yellow-500/20 text-xs font-normal">
                  Analyzing...
                </Badge>
              )}
              {data.status === "error" && (
                <Badge variant="outline" className="bg-red-500/10 text-red-500 border-red-500/20 text-xs font-normal">
                  Failed
                </Badge>
              )}
            </CardTitle>
            <CardDescription className="flex items-center gap-4 mt-2">
              <a 
                href={data.website_url} 
                target="_blank" 
                rel="noreferrer"
                className="flex items-center gap-1 text-blue-400 hover:underline"
              >
                <Globe className="h-3 w-3" />
                {data.website_url.replace(/^https?:\/\/(www\.)?/, '')}
              </a>
              <span className="text-zinc-600 flex items-center gap-1">
                <RefreshCw className="h-3 w-3" />
                Last updated: {data.last_analyzed_at ? format(new Date(data.last_analyzed_at), "MMM d, yyyy h:mm a") : "Never"}
              </span>
            </CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            disabled={isProcessing || refreshMutation.isPending || isRefetching}
            onClick={() => refreshMutation.mutate(data.id)}
            className="border-zinc-800 bg-zinc-900 text-zinc-300 hover:text-white hover:bg-zinc-800"
          >
            <RefreshCw className={`mr-2 h-3 w-3 ${(refreshMutation.isPending || isProcessing || isRefetching) ? "animate-spin" : ""}`} />
            Refresh Data
          </Button>
        </div>
      </CardHeader>

      <ScrollArea className="flex-1 p-6">
        {isProcessing ? (
          <div className="flex flex-col items-center justify-center h-full py-20 text-zinc-500">
            <Loader2 className="h-8 w-8 animate-spin mb-4 text-zinc-400" />
            <p className="text-white font-medium mb-1">Analysis in Progress</p>
            <p className="text-sm text-center max-w-sm">
              We are currently crawling the website and generating insights with AI. This page will update automatically.
            </p>
          </div>
        ) : (
          <div className="space-y-8">
            
            {/* Overview / Summary */}
            {(data.raw_summary || data.overview) && (
              <section className="space-y-3">
                <h3 className="text-lg font-medium text-white flex items-center gap-2">
                  <FileText className="h-5 w-5 text-zinc-400" />
                  AI Summary & Overview
                </h3>
                <div className="bg-zinc-900 border border-zinc-800 rounded-md p-4 text-zinc-300 text-sm leading-relaxed whitespace-pre-wrap">
                  {data.raw_summary || data.overview}
                </div>
              </section>
            )}

            {/* Products & Services */}
            {data.products_services && data.products_services.length > 0 && (
              <section className="space-y-3">
                <h3 className="text-lg font-medium text-white flex items-center gap-2">
                  <Briefcase className="h-5 w-5 text-zinc-400" />
                  Products & Services
                </h3>
                <div className="flex flex-wrap gap-2">
                  {data.products_services.map((product, idx) => (
                    <Badge key={idx} variant="secondary" className="bg-zinc-800 text-zinc-200 hover:bg-zinc-700">
                      {product}
                    </Badge>
                  ))}
                </div>
              </section>
            )}

            {/* Tech Stack */}
            {data.tech_stack && data.tech_stack.length > 0 && (
              <section className="space-y-3">
                <h3 className="text-lg font-medium text-white flex items-center gap-2">
                  <Code className="h-5 w-5 text-zinc-400" />
                  Tech Stack
                </h3>
                <div className="flex flex-wrap gap-2">
                  {data.tech_stack.map((tech, idx) => (
                    <Badge key={idx} variant="outline" className="border-zinc-700 text-zinc-300">
                      {tech}
                    </Badge>
                  ))}
                </div>
              </section>
            )}

            {/* Links and Contact Info */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <section className="space-y-3">
                <h3 className="text-lg font-medium text-white flex items-center gap-2">
                  <Globe className="h-5 w-5 text-zinc-400" />
                  Important Links
                </h3>
                <div className="space-y-2 bg-zinc-900 border border-zinc-800 rounded-md p-4">
                  {data.careers_url ? (
                    <div>
                      <p className="text-xs text-zinc-500 font-medium uppercase mb-1">Careers Page</p>
                      <a href={data.careers_url} target="_blank" rel="noreferrer" className="text-sm text-blue-400 hover:underline break-all block">
                        {data.careers_url}
                      </a>
                    </div>
                  ) : (
                    <p className="text-sm text-zinc-500">No careers page found.</p>
                  )}
                  <div className="h-px bg-zinc-800 my-2" />
                  {data.about_url ? (
                    <div>
                      <p className="text-xs text-zinc-500 font-medium uppercase mb-1">About Page</p>
                      <a href={data.about_url} target="_blank" rel="noreferrer" className="text-sm text-blue-400 hover:underline break-all block">
                        {data.about_url}
                      </a>
                    </div>
                  ) : (
                    <p className="text-sm text-zinc-500">No about page found.</p>
                  )}
                </div>
              </section>

              <section className="space-y-3">
                <h3 className="text-lg font-medium text-white flex items-center gap-2">
                  <Mail className="h-5 w-5 text-zinc-400" />
                  Contact Info
                </h3>
                <div className="bg-zinc-900 border border-zinc-800 rounded-md p-4">
                  {Object.keys(data.contact_info || {}).length > 0 ? (
                    <div className="space-y-2">
                      {Object.entries(data.contact_info).map(([key, value]) => (
                        <div key={key}>
                          <p className="text-xs text-zinc-500 font-medium uppercase mb-1">{key}</p>
                          <p className="text-sm text-zinc-300 break-all">{String(value)}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-zinc-500">No structured contact info found.</p>
                  )}
                </div>
              </section>
            </div>

            {data.error && (
              <section className="space-y-3">
                <div className="bg-red-500/10 border border-red-500/20 rounded-md p-4 flex gap-3">
                  <AlertTriangle className="h-5 w-5 text-red-400 shrink-0" />
                  <div>
                    <h4 className="text-sm font-medium text-red-400">Analysis Error</h4>
                    <p className="text-sm text-red-400/80 mt-1">{data.error}</p>
                  </div>
                </div>
              </section>
            )}
          </div>
        )}
      </ScrollArea>
    </Card>
  );
}
