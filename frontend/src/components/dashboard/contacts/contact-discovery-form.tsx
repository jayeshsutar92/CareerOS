"use client";

import { useState } from "react";
import { Plus, X, Search, Loader2 } from "lucide-react";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useDiscoverContacts } from "@/hooks/use-contacts";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const formSchema = z.object({
  company_name: z.string().min(1, "Company name is required"),
  source_urls: z
    .array(
      z.object({
        value: z.string().url("Please enter a valid URL (e.g., https://...)"),
      })
    )
    .min(1, "At least one source URL is required")
    .max(10, "Maximum of 10 source URLs allowed"),
});

export function ContactDiscoveryForm() {
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const discoverContacts = useDiscoverContacts();

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      company_name: "",
      source_urls: [{ value: "" }],
    },
  });

  const { fields, append, remove } = useFieldArray({
    name: "source_urls",
    control,
  });

  const onSubmit = async (values: z.infer<typeof formSchema>) => {
    setSuccessMessage(null);
    try {
      await discoverContacts.mutateAsync({
        company_name: values.company_name,
        source_urls: values.source_urls.map((u) => u.value),
        run_in_background: true,
      });
      setSuccessMessage("Discovery job started. Contacts will appear in the table shortly.");
      reset();
    } catch {
      // Error will be handled by mutation, but we catch it here to prevent default
    }
  };

  return (
    <Card className="bg-zinc-900 border-zinc-800">
      <CardHeader>
        <CardTitle className="text-lg text-white">Discover Contacts</CardTitle>
        <CardDescription className="text-zinc-400">
          Find hiring managers and recruiters by providing a company name and relevant URLs (e.g., a careers page or job posting).
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {successMessage && (
            <div className="rounded-md border border-green-500/20 bg-green-500/10 p-3 text-sm text-green-400">
              {successMessage}
            </div>
          )}
          {discoverContacts.isError && (
            <div className="rounded-md border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-400">
              Failed to start discovery. Please check your inputs and try again.
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="company_name" className="text-zinc-300">Company Name</Label>
            <Input
              id="company_name"
              placeholder="e.g. Acme Corp"
              {...register("company_name")}
              className="bg-zinc-950 border-zinc-800 text-white placeholder:text-zinc-600 focus-visible:ring-zinc-700"
            />
            {errors.company_name && (
              <p className="text-sm text-red-400">{errors.company_name.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label className="text-zinc-300">Source URLs</Label>
            {fields.map((field, index) => (
              <div key={field.id} className="flex gap-2">
                <div className="flex-1">
                  <Input
                    placeholder="https://example.com/careers"
                    {...register(`source_urls.${index}.value` as const)}
                    className="bg-zinc-950 border-zinc-800 text-white placeholder:text-zinc-600 focus-visible:ring-zinc-700"
                  />
                  {errors.source_urls?.[index]?.value && (
                    <p className="mt-1 text-sm text-red-400">
                      {errors.source_urls[index]?.value?.message}
                    </p>
                  )}
                </div>
                {fields.length > 1 && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => remove(index)}
                    className="shrink-0 text-zinc-500 hover:text-white hover:bg-zinc-800"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                )}
              </div>
            ))}
            {errors.source_urls?.root && (
              <p className="text-sm text-red-400">{errors.source_urls.root.message}</p>
            )}
            
            {fields.length < 10 && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => append({ value: "" })}
                className="mt-2 text-xs border-zinc-800 text-zinc-300 hover:text-white hover:bg-zinc-800"
              >
                <Plus className="mr-2 h-3 w-3" />
                Add URL
              </Button>
            )}
          </div>

          <Button
            type="submit"
            disabled={discoverContacts.isPending}
            className="w-full bg-white text-black hover:bg-zinc-200"
          >
            {discoverContacts.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Discovering...
              </>
            ) : (
              <>
                <Search className="mr-2 h-4 w-4" />
                Discover Contacts
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
