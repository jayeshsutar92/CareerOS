"use client";

import { Settings } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { PageHeader } from "@/components/dashboard/page-header";

export default function SettingsPage() {
  const { user } = useAuth();

  return (
    <div className="space-y-8">
      <PageHeader
        title="Settings"
        description="Manage your account and preferences."
        icon={Settings}
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Settings" },
        ]}
      />

      <div className="max-w-2xl space-y-6">
        <div className="rounded-lg border border-white/10 bg-white/[0.025] p-6">
          <h2 className="text-base font-medium text-white">Profile</h2>
          <div className="mt-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-zinc-500">Name</span>
              <span className="text-sm text-zinc-300">
                {user?.full_name || "—"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-zinc-500">Email</span>
              <span className="text-sm text-zinc-300">
                {user?.email || "—"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-zinc-500">Account status</span>
              <span className="inline-flex items-center gap-1.5 text-sm">
                <span className="size-1.5 rounded-full bg-green-500" />
                <span className="text-zinc-300">Active</span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
