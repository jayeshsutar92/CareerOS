"use client";

import { Loader2, Search } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { toast } from "sonner";
import { useDiscoverLeads } from "@/hooks/use-lead-discovery";

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
      const response = await discoverLeads.mutateAsync({
        location: values.location,
        workMode: values.workMode,
        batchSize: values.batchSize,
      });
      toast.success(
        `Successfully discovered ${response.contacts_discovered} leads in ${values.location} (${values.workMode}).`
      );
    } catch (error: any) {
      const errorMessage = error.response?.data?.error?.message || error.response?.data?.detail || "Failed to start lead discovery. Please try again.";
      toast.error(errorMessage);
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
            disabled={discoverLeads.isPending}
            className="w-full bg-white text-black hover:bg-zinc-200"
          >
            {discoverLeads.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Discovering...
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
