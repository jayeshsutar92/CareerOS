"use client";

import { useState, useRef, useEffect } from "react";
import { Loader2, Search } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import { useDiscoverLeads } from "@/hooks/use-lead-discovery";
import { contactService } from "@/services/contacts";
import type { ContactRead } from "@/types/contact";
import {
  DiscoveredCompany,
  getLeadDiscoveryTaskOutput,
  leadDiscoveryService,
} from "@/services/lead-discovery";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const formSchema = z.object({
  location: z.string().min(1, "Location is required"),
  workMode: z.string(),
  batchSize: z.coerce.number().min(1).max(50),
});

export function LeadDiscoveryForm() {
  const discoverLeads = useDiscoverLeads();
  const queryClient = useQueryClient();
  const [pollingStatus, setPollingStatus] = useState<string | null>(null);
  const [discoveryResult, setDiscoveryResult] = useState<{
    location: string;
    contactsDiscovered: number;
    companies: DiscoveredCompany[];
    contacts: ContactRead[];
  } | null>(null);

  const isMounted = useRef(true);
  const activeTaskRef = useRef<{ taskId: string; timeoutId: NodeJS.Timeout | null } | null>(null);

  useEffect(() => {
    return () => {
      isMounted.current = false;
      const active = activeTaskRef.current;
      if (active) {
        if (active.timeoutId) clearTimeout(active.timeoutId);
        if (active.taskId) {
          leadDiscoveryService.cancelTask(active.taskId).catch(() => {});
        }
      }
    };
  }, []);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<z.infer<typeof formSchema>>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(formSchema as any),
    defaultValues: {
      location: "Mumbai",
      workMode: "remote",
      batchSize: 5,
    },
  });

  const onSubmit = async (values: z.infer<typeof formSchema>) => {
    try {
      setPollingStatus("searching / processing");
      setDiscoveryResult(null);
      
      // Cancel any existing task
      if (activeTaskRef.current?.taskId) {
        if (activeTaskRef.current.timeoutId) clearTimeout(activeTaskRef.current.timeoutId);
        leadDiscoveryService.cancelTask(activeTaskRef.current.taskId).catch(() => {});
      }
      
      const response = await discoverLeads.mutateAsync({
        location: values.location,
        workMode: values.workMode,
        batchSize: values.batchSize,
      });

      if (!response.task_id) {
        if (isMounted.current) {
          setPollingStatus("search failure");
          toast.error("Failed to enqueue task.");
          setTimeout(() => { if (isMounted.current) setPollingStatus(null); }, 3000);
        }
        return;
      }
      
      activeTaskRef.current = { taskId: response.task_id, timeoutId: null };

      const poll = async () => {
        if (!isMounted.current) return;
        try {
          const res = await leadDiscoveryService.getTaskStatus(response.task_id!);
          if (!isMounted.current) return;
          
          if (res.status !== "succeeded" && res.status !== "failed") {
            const timeoutId = setTimeout(poll, 2000);
            if (activeTaskRef.current) activeTaskRef.current.timeoutId = timeoutId;
          } else {
            activeTaskRef.current = null; // Task finished
            if (res.status === "succeeded") {
              const agentOutput = getLeadDiscoveryTaskOutput(res.result);

              if (agentOutput?.status === "failed") {
                setPollingStatus("search failure");
                toast.error(agentOutput.error || "Company URL discovery failed");
                setTimeout(() => { if (isMounted.current) setPollingStatus(null); }, 3000);
              } else {
                const contactsDiscovered = agentOutput?.contacts_discovered || 0;
                const companiesDiscovered = agentOutput?.discovered_companies?.length || 0;
                
                if (companiesDiscovered === 0) {
                  setPollingStatus("no results");
                  toast.error("No companies found matching criteria");
                } else if (contactsDiscovered === 0) {
                  setPollingStatus(`companies found: ${companiesDiscovered}`);
                  toast.success(`Discovered ${companiesDiscovered} companies, but no contacts found.`);
                } else if (contactsDiscovered < values.batchSize) {
                  setPollingStatus(`partial results: ${contactsDiscovered} found`);
                  toast.success(`Partial discovery: ${contactsDiscovered} leads found across ${companiesDiscovered} companies.`);
                } else {
                  setPollingStatus(`contacts found: ${contactsDiscovered}`);
                  toast.success(`Successfully discovered ${contactsDiscovered} leads.`);
                }

                const processedContactIds = new Set(agentOutput?.processed_contact_ids || []);
                let discoveredContacts: ContactRead[] = [];

                if (processedContactIds.size > 0) {
                  try {
                    const contactsResponse = await contactService.getContacts({
                      page: 1,
                      page_size: 100,
                    });
                    discoveredContacts = contactsResponse.items.filter((contact) =>
                      processedContactIds.has(contact.id),
                    );
                  } catch {}
                }
                
                if (isMounted.current) {
                  setDiscoveryResult({
                    location: agentOutput?.location || values.location,
                    contactsDiscovered,
                    companies: agentOutput?.discovered_companies || [],
                    contacts: discoveredContacts,
                  });
                }

                queryClient.invalidateQueries({ queryKey: ["contacts"] });
                queryClient.invalidateQueries({ queryKey: ["scheduled-emails"] });
                queryClient.invalidateQueries({ queryKey: ["company-intelligence"] });
                setTimeout(() => { if (isMounted.current) setPollingStatus(null); }, 3000);
              }
            } else if (res.status === "failed") {
              setPollingStatus("search failure");
              toast.error(res.error || "Company URL discovery failed");
              setTimeout(() => { if (isMounted.current) setPollingStatus(null); }, 3000);
            }
          }
        } catch {
          if (!isMounted.current) return;
          activeTaskRef.current = null;
          setPollingStatus("search failure");
          toast.error("Failed to check task status.");
          setTimeout(() => { if (isMounted.current) setPollingStatus(null); }, 3000);
        }
      };

      const timeoutId = setTimeout(poll, 2000);
      if (activeTaskRef.current) activeTaskRef.current.timeoutId = timeoutId;
      
    } catch (error: any) {
      if (!isMounted.current) return;
      setPollingStatus("search failure");
      const errorMessage = error.response?.data?.error?.message || error.response?.data?.detail || "Failed to start lead discovery. Please try again.";
      toast.error(errorMessage);
      setTimeout(() => { if (isMounted.current) setPollingStatus(null); }, 3000);
    }
  };

  return (
    <Card className="bg-zinc-900 border-zinc-800">
      <CardHeader>
        <CardTitle className="text-lg text-white">Lead Discovery</CardTitle>
        <CardDescription className="text-zinc-400">
          Automatically discover new leads based on location and work mode.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="location" className="text-zinc-300">
              Location
            </Label>
            <Input
              id="location"
              {...register("location")}
              className="bg-zinc-950 border-zinc-800 text-white placeholder:text-zinc-600 focus-visible:ring-zinc-700"
            />
            {errors.location && (
              <p className="text-sm text-red-400">{errors.location.message}</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-zinc-300">Work Mode</Label>
              <Select
                value={watch("workMode")}
                onValueChange={(val) => setValue("workMode", val)}
              >
                <SelectTrigger className="w-full bg-zinc-950 border-zinc-800 text-white">
                  <SelectValue placeholder="Select mode" />
                </SelectTrigger>
                <SelectContent className="bg-zinc-950 border-zinc-800 text-white">
                  <SelectItem value="remote">Remote</SelectItem>
                  <SelectItem value="on-site">On-site</SelectItem>
                  <SelectItem value="both">Both</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="batchSize" className="text-zinc-300">
                Batch Size
              </Label>
              <Input
                id="batchSize"
                type="number"
                {...register("batchSize")}
                className="bg-zinc-950 border-zinc-800 text-white placeholder:text-zinc-600 focus-visible:ring-zinc-700"
              />
              {errors.batchSize && (
                <p className="text-sm text-red-400">
                  {errors.batchSize.message}
                </p>
              )}
            </div>
          </div>

          <Button
            type="submit"
            disabled={discoverLeads.isPending || pollingStatus !== null}
            className="w-full bg-white text-black hover:bg-zinc-200"
          >
            {discoverLeads.isPending || pollingStatus !== null ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {pollingStatus ? pollingStatus : "Starting..."}
              </>
            ) : (
              <>
                <Search className="mr-2 h-4 w-4" />
                Start Discovery
              </>
            )}
          </Button>
        </form>

        {discoveryResult && (
          <div className="mt-6 space-y-3 border-t border-zinc-800 pt-6">
            <h4 className="text-sm font-medium text-white">
              Discovery Results for {discoveryResult.location}
            </h4>
            <div className="rounded-md border border-zinc-800 bg-zinc-950/50 p-4">
              <div className="text-sm text-zinc-400 mb-3">
                Found {discoveryResult.contactsDiscovered} contacts across {discoveryResult.companies.length} companies.
              </div>
              {discoveryResult.companies.length > 0 && (
                <ul className="space-y-2">
                  {discoveryResult.companies.map((company, idx) => (
                    <li key={`${company.url}-${idx}`} className="flex justify-between items-center text-sm">
                      <div className="flex items-center space-x-2 truncate pr-4">
                        <span className="text-zinc-300 font-medium truncate">{company.name}</span>
                        <a href={company.url} target="_blank" rel="noreferrer" className="text-blue-400 hover:underline text-xs truncate max-w-[150px]">
                          {company.url}
                        </a>
                      </div>
                      <span className="text-zinc-500 whitespace-nowrap bg-zinc-900 px-2 py-1 rounded text-xs">
                        {company.contacts_count} contacts
                      </span>
                    </li>
                  ))}
                </ul>
              )}
              {discoveryResult.contacts.length > 0 && (
                <ul className="mt-3 space-y-2 border-t border-zinc-800 pt-3">
                  {discoveryResult.contacts.map((contact) => (
                    <li key={contact.id} className="flex justify-between gap-4 text-sm">
                      <div className="min-w-0">
                        <p className="truncate font-medium text-zinc-200">{contact.name}</p>
                        <p className="truncate text-zinc-500">{contact.role} · {contact.company_name}</p>
                      </div>
                      <span className="shrink-0 text-zinc-500">Contact</span>
                    </li>
                  ))}
                </ul>
              )}
              {discoveryResult.companies.length === 0 && discoveryResult.contacts.length === 0 && (
                <p className="text-sm text-zinc-500">No results found for this discovery.</p>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
