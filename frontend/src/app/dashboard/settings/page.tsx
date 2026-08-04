"use client";

import { Settings } from "lucide-react";
import { PageHeader } from "@/components/dashboard/page-header";
import { ProfileSettingsForm } from "@/components/dashboard/settings/profile-settings-form";
import { OutreachSettingsForm } from "@/components/dashboard/settings/outreach-settings-form";

export default function SettingsPage() {
  return (
    <div className="space-y-8 pb-12">
      <PageHeader
        title="Settings"
        description="Manage your profile, preferences, and AI outreach instructions."
        icon={Settings}
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Settings" },
        ]}
      />

      <div className="max-w-4xl space-y-8">
        <ProfileSettingsForm />
        <OutreachSettingsForm />
      </div>
    </div>
  );
}
