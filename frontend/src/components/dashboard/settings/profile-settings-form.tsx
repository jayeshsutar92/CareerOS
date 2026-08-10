"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { toast } from "sonner";
import { Loader2, Save } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useSettingsStore } from "@/store/settings";
import { useAuth } from "@/hooks/use-auth";

const profileSchema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().email("Please enter a valid email"),
  designation: z.string().optional(),
  bio: z.string().max(500, "Bio must be less than 500 characters").optional(),
  skills: z.string().optional(),
  portfolioLinks: z.string().optional(),
  githubLink: z.string().optional(),
  linkedinLink: z.string().optional(),
});

type ProfileFormValues = z.infer<typeof profileSchema>;

export function ProfileSettingsForm() {
  const { user } = useAuth();
  const profile = useSettingsStore((state) => state.profile);
  const updateProfile = useSettingsStore((state) => state.updateProfile);
  const [isSaving, setIsSaving] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isDirty },
    reset,
  } = useForm<ProfileFormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(profileSchema as any),
    defaultValues: {
      name: profile.name || user?.full_name || "",
      email: profile.email || user?.email || "",
      designation: profile.designation || "",
      bio: profile.bio || "",
      skills: profile.skills || "",
      portfolioLinks: profile.portfolioLinks || "",
      githubLink: profile.githubLink || "",
      linkedinLink: profile.linkedinLink || "",
    },
  });

  const onSubmit = async (values: ProfileFormValues) => {
    setIsSaving(true);
    try {
      // Simulate API call or just save to store immediately
      await new Promise((resolve) => setTimeout(resolve, 600));
      updateProfile(values);
      toast.success("Profile settings saved successfully");
      reset(values); // Reset isDirty state
    } catch (error) {
      toast.error("Failed to save profile settings");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.025] p-6">
      <h2 className="text-lg font-medium text-white mb-6">Profile Settings</h2>
      
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="name" className="text-zinc-300">Full Name</Label>
            <Input
              id="name"
              placeholder="John Doe"
              {...register("name")}
              className="bg-black/50 border-white/10 text-white"
            />
            {errors.name && <p className="text-sm text-red-500">{errors.name.message}</p>}
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="email" className="text-zinc-300">Email Address</Label>
            <Input
              id="email"
              type="email"
              placeholder="john@example.com"
              {...register("email")}
              className="bg-black/50 border-white/10 text-white"
            />
            {errors.email && <p className="text-sm text-red-500">{errors.email.message}</p>}
          </div>

          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="designation" className="text-zinc-300">Current Role / Designation</Label>
            <Input
              id="designation"
              placeholder="e.g. Senior Frontend Developer"
              {...register("designation")}
              className="bg-black/50 border-white/10 text-white"
            />
          </div>

          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="bio" className="text-zinc-300">Short Professional Bio</Label>
            <Textarea
              id="bio"
              placeholder="Briefly describe your professional background..."
              {...register("bio")}
              className="bg-black/50 border-white/10 text-white resize-none"
              rows={3}
            />
            {errors.bio && <p className="text-sm text-red-500">{errors.bio.message}</p>}
          </div>

          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="skills" className="text-zinc-300">Skills (comma separated)</Label>
            <Input
              id="skills"
              placeholder="React, TypeScript, Next.js, Node.js"
              {...register("skills")}
              className="bg-black/50 border-white/10 text-white"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="portfolioLinks" className="text-zinc-300">Portfolio URL</Label>
            <Input
              id="portfolioLinks"
              placeholder="https://yourportfolio.com"
              {...register("portfolioLinks")}
              className="bg-black/50 border-white/10 text-white"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="githubLink" className="text-zinc-300">GitHub URL</Label>
            <Input
              id="githubLink"
              placeholder="https://github.com/username"
              {...register("githubLink")}
              className="bg-black/50 border-white/10 text-white"
            />
          </div>

          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="linkedinLink" className="text-zinc-300">LinkedIn URL (Optional)</Label>
            <Input
              id="linkedinLink"
              placeholder="https://linkedin.com/in/username"
              {...register("linkedinLink")}
              className="bg-black/50 border-white/10 text-white"
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
            Save Profile
          </Button>
        </div>
      </form>
    </div>
  );
}
