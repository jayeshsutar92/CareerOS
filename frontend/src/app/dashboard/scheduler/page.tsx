"use client";

import { Calendar } from "lucide-react";
import { PageHeader } from "@/components/dashboard/page-header";
import { EmptyState } from "@/components/dashboard/empty-state";

export default function SchedulerPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Scheduler"
        description="Schedule and track email delivery."
        icon={Calendar}
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Scheduler" },
        ]}
      />

      <EmptyState
        icon={Calendar}
        title="No scheduled emails"
        description="Once you generate personalized emails, you can schedule them for delivery from here."
      />
    </div>
  );
}
