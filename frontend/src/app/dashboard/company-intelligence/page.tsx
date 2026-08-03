"use client";

import { useState } from "react";
import { Building2 } from "lucide-react";
import { PageHeader } from "@/components/dashboard/page-header";
import { CompanyAnalysisForm } from "@/components/dashboard/company/company-analysis-form";
import { CompanyList } from "@/components/dashboard/company/company-list";
import { CompanyDetails } from "@/components/dashboard/company/company-details";

export default function CompanyIntelligencePage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  return (
    <div className="space-y-8 h-full flex flex-col">
      <PageHeader
        title="Company Intelligence"
        description="Research and analyze target companies using AI."
        icon={Building2}
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Company Intelligence" },
        ]}
      />

      <div className="grid gap-6 lg:grid-cols-12">
        <div className="lg:col-span-4 space-y-6">
          <CompanyAnalysisForm onSuccess={(id) => setSelectedId(id)} />
          <CompanyList selectedId={selectedId} onSelect={setSelectedId} />
        </div>
        <div className="lg:col-span-8">
          <CompanyDetails id={selectedId} />
        </div>
      </div>
    </div>
  );
}
