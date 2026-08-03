"use client";

import { Mail } from "lucide-react";
import { PageHeader } from "@/components/dashboard/page-header";
import { EmptyState } from "@/components/dashboard/empty-state";

export default function EmailPersonalizationPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Email Personalization"
        description="Generate personalized outreach emails with AI."
        icon={Mail}
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Email Personalization" },
        ]}
      />

      <EmptyState
        icon={Mail}
        title="No emails generated"
        description="Select a company and contact, choose a template, and let AI craft a personalized outreach email."
      />
    </div>
  );
}
