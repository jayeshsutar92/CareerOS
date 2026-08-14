"use client";

import { useMemo } from "react";
import { Home } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { PageHeader } from "@/components/dashboard/page-header";
import { LeadDiscoveryForm } from "@/components/dashboard/lead-discovery-form";
import { ContactsTable } from "@/components/dashboard/contacts/contacts-table";
import { useContacts } from "@/hooks/use-contacts";
import { useScheduledEmails } from "@/hooks/use-scheduler";

export default function DashboardPage() {
  const { user } = useAuth();
  
  // Fetch stats data
  const { data: contactsData } = useContacts({ page: 1, page_size: 1 });
  const { data: emailsData } = useScheduledEmails();

  const stats = useMemo(() => {
    let drafted = 0;
    let scheduled = 0;
    let sent = 0;
    let failed = 0;

    if (emailsData?.data) {
      emailsData.data.forEach((email) => {
        if (email.status === "draft") drafted++;
        else if (email.status === "scheduled") scheduled++;
        else if (email.status === "sent") sent++;
        else if (email.status === "failed") failed++;
      });
    }

    return {
      discovered: contactsData?.total || 0,
      drafted,
      scheduled,
      sent,
      failed,
    };
  }, [contactsData, emailsData]);

  return (
    <div className="space-y-8 pb-12">
      <PageHeader
        title="Dashboard"
        description={`Welcome back, ${user?.full_name || "there"}. Your workspace is ready.`}
        icon={Home}
      />

      {/* Summary Section */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {[
          { title: "Discovered", value: stats.discovered, desc: "Contacts" },
          { title: "Drafted", value: stats.drafted, desc: "Emails ready" },
          { title: "Scheduled", value: stats.scheduled, desc: "Pending delivery" },
          { title: "Sent", value: stats.sent, desc: "Successfully delivered" },
          { title: "Failed", value: stats.failed, desc: "Delivery errors" },
        ].map((card) => (
          <div
            key={card.title}
            className="rounded-lg border border-white/10 bg-white/[0.025] p-5 flex flex-col justify-between"
          >
            <p className="text-sm text-zinc-500">{card.title}</p>
            <p className="mt-2 text-3xl font-semibold text-white">
              {card.value}
            </p>
            <p className="mt-1 text-xs text-zinc-500">{card.desc}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Lead Discovery Controls */}
        <div className="lg:col-span-1 space-y-8">
          <LeadDiscoveryForm />
        </div>

        {/* Contact Results */}
        <div className="lg:col-span-2 space-y-8">
          <div className="rounded-lg border border-white/10 bg-zinc-950/50 p-6">
            <div className="mb-4">
              <h2 className="text-xl font-semibold text-white">Contact Results</h2>
              <p className="text-sm text-zinc-400">Recently discovered HR and recruiter contacts.</p>
            </div>
            <ContactsTable />
          </div>
        </div>
      </div>
    </div>
  );
}
