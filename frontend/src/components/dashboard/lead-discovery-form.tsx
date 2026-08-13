"use client";

import { useState } from "react";
import { Loader2, Search } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import { useDiscoverLeads } from "@/hooks/use-lead-discovery";
import { leadDiscoveryService } from "@/services/lead-discovery";

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
      const response = await discoverLeads.mutateAsync({
        location: values.location,
        workMode: values.workMode,
        batchSize: values.batchSize,
      });

      if (!response.task_id) {
        setPollingStatus("search failure");
        toast.error("Failed to enqueue task.");
        setTimeout(() => setPollingStatus(null), 3000);
        return;
      }

      const poll = async () => {
        try {
          const res = await leadDiscoveryService.getTaskStatus(response.task_id!);
          if (["processing", "queued", "running", "scheduled"].includes(res.status)) {
            setTimeout(poll, 2000);
          } else if (res.status === "succeeded") {
            // Extract the agent output from the orchestration result
            const agentOutput = res.result?.results?.[0]?.output || res.result;
            
            if (agentOutput?.status === "failed") {
              setPollingStatus("search failure");
              toast.error(agentOutput.error || "Company URL discovery failed");
              setTimeout(() => setPollingStatus(null), 3000);
            } else {
              const contactsDiscovered = agentOutput?.contacts_discovered || 0;
              if (contactsDiscovered === 0) {
                setPollingStatus("no results");
                toast.error("No contacts found on discovered domains");
              } else if (contactsDiscovered < values.batchSize) {
                setPollingStatus(`partial results: ${contactsDiscovered} found`);
                toast.success(`Partial discovery: ${contactsDiscovered} leads found.`);
              } else {
                setPollingStatus(`contacts found: ${contactsDiscovered}`);
                toast.success(`Successfully discovered ${contactsDiscovered} leads.`);
              }
              queryClient.invalidateQueries({ queryKey: ["contacts"] });
              queryClient.invalidateQueries({ queryKey: ["scheduled-emails"] });
              queryClient.invalidateQueries({ queryKey: ["company-intelligence"] });
              setTimeout(() => setPollingStatus(null), 3000);
            }
          } else if (res.status === "failed") {
            setPollingStatus("search failure");
            toast.error(res.error || "Company URL discovery failed");
            setTimeout(() => setPollingStatus(null), 3000);
          }
        } catch (err: any) {
          setPollingStatus("search failure");
          toast.error("Failed to check task status.");
          setTimeout(() => setPollingStatus(null), 3000);
        }
      };

      setTimeout(poll, 2000);
    } catch (error: any) {
      setPollingStatus("search failure");
      const errorMessage = error.response?.data?.error?.message || error.response?.data?.detail || "Failed to start lead discovery. Please try again.";
      toast.error(errorMessage);
      setTimeout(() => setPollingStatus(null), 3000);
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
      </CardContent>
    </Card>
  );
}
