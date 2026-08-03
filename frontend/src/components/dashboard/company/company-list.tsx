"use client";

import { useState } from "react";
import { format } from "date-fns";
import { Search, Loader2, Building2, Globe, ChevronLeft, ChevronRight } from "lucide-react";
import { useCompanyIntelligenceList } from "@/hooks/use-company";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

interface CompanyListProps {
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function CompanyList({ selectedId, onSelect }: CompanyListProps) {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  const { data, isLoading, isError } = useCompanyIntelligenceList({
    page,
    page_size: 15,
    search: debouncedSearch || undefined,
  });

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearch(e.target.value);
    const timeoutId = setTimeout(() => {
      setDebouncedSearch(e.target.value);
      setPage(1);
    }, 500);
    return () => clearTimeout(timeoutId);
  };

  return (
    <div className="flex flex-col h-[600px] border border-zinc-800 rounded-md bg-zinc-900/50">
      <div className="p-4 border-b border-zinc-800">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
          <Input
            placeholder="Search companies..."
            value={search}
            onChange={handleSearchChange}
            className="pl-9 bg-zinc-950 border-zinc-800 text-white placeholder:text-zinc-600 focus-visible:ring-zinc-700"
          />
        </div>
      </div>

      <ScrollArea className="flex-1">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-40 text-zinc-500">
            <Loader2 className="h-6 w-6 animate-spin mb-2" />
            <p className="text-sm">Loading companies...</p>
          </div>
        ) : isError ? (
          <div className="flex items-center justify-center h-40 text-red-400 text-sm p-4 text-center">
            Failed to load companies.
          </div>
        ) : !data || data.items.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 text-zinc-500 p-4 text-center">
            <Building2 className="h-8 w-8 mb-2 opacity-50" />
            <p className="text-sm">No companies found.</p>
          </div>
        ) : (
          <div className="flex flex-col">
            {data.items.map((company) => (
              <button
                key={company.id}
                onClick={() => onSelect(company.id)}
                className={cn(
                  "flex flex-col items-start text-left p-4 border-b border-zinc-800/50 transition-colors hover:bg-zinc-800/80",
                  selectedId === company.id ? "bg-zinc-800 border-l-2 border-l-white" : ""
                )}
              >
                <div className="flex items-start justify-between w-full mb-1">
                  <span className="font-medium text-white truncate pr-2">
                    {company.company_name}
                  </span>
                  {company.status === "processing" || company.status === "queued" ? (
                    <Badge variant="outline" className="bg-yellow-500/10 text-yellow-500 border-yellow-500/20 text-[10px] px-1.5 shrink-0">
                      Processing
                    </Badge>
                  ) : company.status === "error" ? (
                    <Badge variant="outline" className="bg-red-500/10 text-red-500 border-red-500/20 text-[10px] px-1.5 shrink-0">
                      Error
                    </Badge>
                  ) : null}
                </div>
                
                <div className="flex items-center text-xs text-zinc-400 w-full mb-2">
                  <Globe className="h-3 w-3 mr-1 shrink-0" />
                  <span className="truncate">{company.website_url.replace(/^https?:\/\/(www\.)?/, '')}</span>
                </div>
                
                <div className="text-[10px] text-zinc-600 mt-auto">
                  {format(new Date(company.created_at), "MMM d, yyyy")}
                </div>
              </button>
            ))}
          </div>
        )}
      </ScrollArea>

      {data && data.pages > 1 && (
        <div className="p-3 border-t border-zinc-800 flex items-center justify-between bg-zinc-900">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1 || isLoading}
            className="h-7 w-7 text-zinc-400 hover:text-white hover:bg-zinc-800"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-xs text-zinc-500">
            {page} / {data.pages}
          </span>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
            disabled={page === data.pages || isLoading}
            className="h-7 w-7 text-zinc-400 hover:text-white hover:bg-zinc-800"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  );
}
