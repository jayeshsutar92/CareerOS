"use client";

import { Building2 } from "lucide-react";
import { PageHeader } from "@/components/dashboard/page-header";
import { EmptyState } from "@/components/dashboard/empty-state";

export default function CompanyIntelligencePage() {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Company Intelligence"
        description="Research and analyze target companies."
        icon={Building2}
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Company Intelligence" },
        ]}
      />

      <EmptyState
        icon={Building2}
        title="No companies analyzed"
        description="Add a company URL to start generating intelligence reports with AI-powered analysis."
      />
    </div>
  );
}
