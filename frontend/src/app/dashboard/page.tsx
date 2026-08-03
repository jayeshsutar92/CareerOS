"use client";

import { Home } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { PageHeader } from "@/components/dashboard/page-header";

export default function DashboardPage() {
  const { user } = useAuth();

  return (
    <div className="space-y-8">
      <PageHeader
        title="Dashboard"
        description={`Welcome back, ${user?.full_name || "there"}. Your workspace is ready.`}
        icon={Home}
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[
          {
            title: "Opportunity Pipeline",
            value: "—",
            description: "Companies tracked",
          },
          {
            title: "Outreach Drafts",
            value: "—",
            description: "Personalized emails",
          },
          {
            title: "Contacts",
            value: "—",
            description: "Hiring contacts discovered",
          },
        ].map((card) => (
          <div
            key={card.title}
            className="rounded-lg border border-white/10 bg-white/[0.025] p-5"
          >
            <p className="text-sm text-zinc-500">{card.title}</p>
            <p className="mt-2 text-3xl font-semibold text-white">
              {card.value}
            </p>
            <p className="mt-1 text-xs text-zinc-500">{card.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
