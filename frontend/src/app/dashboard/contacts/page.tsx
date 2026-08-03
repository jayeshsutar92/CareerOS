"use client";

import { Users } from "lucide-react";
import { PageHeader } from "@/components/dashboard/page-header";
import { ContactDiscoveryForm } from "@/components/dashboard/contacts/contact-discovery-form";
import { ContactsTable } from "@/components/dashboard/contacts/contacts-table";

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

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-1">
          <ContactDiscoveryForm />
        </div>
        <div className="lg:col-span-2">
          <ContactsTable />
        </div>
      </div>
    </div>
  );
}
