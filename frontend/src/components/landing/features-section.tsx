import {
  BarChart3,
  Building2,
  FileSearch,
  Mail,
  Search,
  Sparkles,
} from "lucide-react";

import { FeatureCard } from "@/components/landing/feature-card";

const features = [
  {
    title: "Company Discovery",
    description: "Find target companies by market, role, funding stage, and hiring signals.",
    icon: Building2,
  },
  {
    title: "Job Discovery",
    description: "Track relevant openings and prioritize the roles that match your goals.",
    icon: Search,
  },
  {
    title: "Company Research",
    description: "Turn scattered company context into concise notes for smarter applications.",
    icon: FileSearch,
  },
  {
    title: "Resume Matching",
    description: "Compare your experience with role requirements and surface practical gaps.",
    icon: Sparkles,
  },
  {
    title: "Personalized Outreach",
    description: "Draft targeted messages that connect your background to each opportunity.",
    icon: Mail,
  },
  {
    title: "Analytics Dashboard",
    description: "Understand your pipeline, outreach performance, and application momentum.",
    icon: BarChart3,
  },
];

export function FeaturesSection() {
  return (
    <section id="features" className="border-b border-white/10 py-20 sm:py-24">
      <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="max-w-2xl">
          <p className="text-sm font-medium text-zinc-500">Features</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-normal text-white sm:text-4xl">
            Everything your job search needs, organized in one place.
          </h2>
          <p className="mt-4 text-base leading-7 text-zinc-400">
            CareerOS brings discovery, research, outreach, and progress tracking into a focused workspace.
          </p>
        </div>

        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((feature) => (
            <FeatureCard key={feature.title} {...feature} />
          ))}
        </div>
      </div>
    </section>
  );
}
