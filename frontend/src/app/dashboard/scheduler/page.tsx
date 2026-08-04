"use client";

import { Calendar } from "lucide-react";
import { PageHeader } from "@/components/dashboard/page-header";
import { ScheduledEmailsTable } from "@/components/dashboard/scheduler/scheduled-emails-table";

export default function SchedulerPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Scheduler & Delivery"
        description="Schedule, track, and manage email delivery."
        icon={Calendar}
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Scheduler" },
        ]}
      />

      <div className="flex flex-col gap-6">
        <ScheduledEmailsTable />
      </div>
    </div>
  );
}
