"use client";

import { Users } from "lucide-react";
import { PageHeader } from "@/components/dashboard/page-header";
import { EmptyState } from "@/components/dashboard/empty-state";

export default function ContactsPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Contacts"
        description="Discover and manage hiring contacts."
        icon={Users}
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Contacts" },
        ]}
      />

      <EmptyState
        icon={Users}
        title="No contacts yet"
        description="Start discovering hiring contacts by running a contact search for your target companies."
      />
    </div>
  );
}
