"use client";

import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { toast } from "sonner";
import { Loader2, Save } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useSettingsStore } from "@/store/settings";

const outreachSchema = z.object({
  emailSignature: z.string().optional(),
  defaultTone: z.string().min(1, "Tone is required"),
  customInstructions: z.string().max(1000, "Custom instructions must be less than 1000 characters").optional(),
  senderPreferences: z.string().optional(),
});

type OutreachFormValues = z.infer<typeof outreachSchema>;

export function OutreachSettingsForm() {
  const outreach = useSettingsStore((state) => state.outreach);
  const updateOutreach = useSettingsStore((state) => state.updateOutreach);
  const [isSaving, setIsSaving] = useState(false);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isDirty },
    reset,
  } = useForm<OutreachFormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(outreachSchema as any),
    defaultValues: {
      emailSignature: outreach.emailSignature || "",
      defaultTone: outreach.defaultTone || "Professional",
      customInstructions: outreach.customInstructions || "",
      senderPreferences: outreach.senderPreferences || "",
    },
  });

  const onSubmit = async (values: OutreachFormValues) => {
    setIsSaving(true);
    try {
      // Simulate API call or just save to store immediately
      await new Promise((resolve) => setTimeout(resolve, 600));
      updateOutreach(values);
      toast.success("Outreach settings saved successfully");
      reset(values); // Reset isDirty state
    } catch (error) {
      toast.error("Failed to save outreach settings");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.025] p-6">
      <h2 className="text-lg font-medium text-white mb-6">Outreach & AI Preferences</h2>
      
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <div className="grid grid-cols-1 gap-6">
          
          <div className="space-y-2">
            <Label htmlFor="defaultTone" className="text-zinc-300">Default Email Tone</Label>
            <Controller
              name="defaultTone"
              control={control}
              render={({ field }) => (
                <Select onValueChange={field.onChange} value={field.value}>
                  <SelectTrigger className="w-full sm:max-w-md bg-black/50 border-white/10 text-white">
                    <SelectValue placeholder="Select tone" />
                  </SelectTrigger>
                  <SelectContent className="bg-zinc-950 border-white/10">
                    <SelectItem value="Professional">Professional & Formal</SelectItem>
                    <SelectItem value="Friendly">Friendly & Approachable</SelectItem>
                    <SelectItem value="Direct">Direct & Concise</SelectItem>
                    <SelectItem value="Persuasive">Persuasive & Confident</SelectItem>
                    <SelectItem value="Casual">Casual & Conversational</SelectItem>
                  </SelectContent>
                </Select>
              )}
            />
            {errors.defaultTone && <p className="text-sm text-red-500">{errors.defaultTone.message}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="customInstructions" className="text-zinc-300">Custom AI Instructions</Label>
            <Textarea
              id="customInstructions"
              placeholder="e.g. Always mention my latest open-source project. Never use the phrase 'I hope this email finds you well'."
              {...register("customInstructions")}
              className="bg-black/50 border-white/10 text-white resize-none"
              rows={4}
            />
            {errors.customInstructions && <p className="text-sm text-red-500">{errors.customInstructions.message}</p>}
            <p className="text-xs text-zinc-500">
              These instructions will be prepended to the AI when generating any personalized email.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="emailSignature" className="text-zinc-300">Preferred Email Signature</Label>
            <Textarea
              id="emailSignature"
              placeholder="Best regards,&#10;John Doe&#10;Senior Developer"
              {...register("emailSignature")}
              className="bg-black/50 border-white/10 text-white resize-none"
              rows={4}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="senderPreferences" className="text-zinc-300">Default Sender Name (Fallback)</Label>
            <Input
              id="senderPreferences"
              placeholder="How your name should appear if not fully resolved"
              {...register("senderPreferences")}
              className="bg-black/50 border-white/10 text-white sm:max-w-md"
            />
          </div>
          
        </div>

        <div className="flex justify-end pt-4">
          <Button 
            type="submit" 
            disabled={!isDirty || isSaving}
            className="gap-2 bg-blue-600 text-white hover:bg-blue-700 border-0"
          >
            {isSaving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            Save Preferences
          </Button>
        </div>
      </form>
    </div>
  );
}
