import Link from "next/link";
import { ArrowRight, Code2 } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function HeroSection() {
  return (
    <section className="relative overflow-hidden border-b border-white/10">
      <div className="absolute inset-x-0 top-0 h-px bg-white/20" aria-hidden="true" />
      <div className="mx-auto grid min-h-[calc(100vh-4rem)] w-full max-w-7xl items-center gap-12 px-4 py-20 sm:px-6 lg:grid-cols-[1.03fr_0.97fr] lg:px-8 lg:py-24">
        <div className="max-w-3xl">
          <p className="mb-5 inline-flex rounded-md border border-white/10 bg-white/[0.03] px-3 py-1 text-sm text-zinc-300">
            Intelligent job search command center
          </p>
          <h1 className="text-5xl font-semibold leading-[1.02] tracking-normal text-white sm:text-6xl lg:text-7xl">
            Your AI Career Operating System
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-zinc-400 sm:text-xl">
            Discover opportunities, research companies, generate personalized outreach, and manage your job search from one intelligent workspace.
          </p>
          <div className="mt-9 flex flex-col gap-3 sm:flex-row">
            <Link
              href="/register"
              className={cn(buttonVariants({ size: "lg" }), "h-11 bg-white px-5 text-black hover:bg-zinc-200")}
            >
              Get Started
              <ArrowRight aria-hidden="true" className="size-4" />
            </Link>
            <Link
              href="#"
              className={cn(
                buttonVariants({ variant: "outline", size: "lg" }),
                "h-11 border-white/15 bg-white/[0.03] px-5 text-white hover:bg-white/10",
              )}
            >
              <Code2 aria-hidden="true" className="size-4" />
              View GitHub
            </Link>
          </div>
        </div>

        <div className="relative">
          <div className="rounded-lg border border-white/10 bg-zinc-950 shadow-2xl shadow-black/40">
            <div className="flex h-11 items-center gap-2 border-b border-white/10 px-4">
              <span className="size-2.5 rounded-full bg-zinc-600" />
              <span className="size-2.5 rounded-full bg-zinc-600" />
              <span className="size-2.5 rounded-full bg-zinc-600" />
              <span className="ml-3 text-xs text-zinc-500">career-workspace</span>
            </div>
            <div className="space-y-5 p-5 sm:p-6">
              <div className="rounded-md border border-white/10 bg-white/[0.03] p-4">
                <div className="mb-3 flex items-center justify-between">
                  <span className="text-sm font-medium text-white">Opportunity Pipeline</span>
                  <span className="text-xs text-zinc-500">Live</span>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { label: "Found", value: 48 },
                    { label: "Matched", value: 19 },
                    { label: "Outreach", value: 7 },
                  ].map((metric) => (
                    <div key={metric.label} className="rounded-md border border-white/10 bg-black/30 p-3">
                      <p className="text-xs text-zinc-500">{metric.label}</p>
                      <p className="mt-2 text-2xl font-semibold text-white">{metric.value}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="grid gap-3">
                {[
                  ["Research", "Company signals summarized for outreach."],
                  ["Resume Match", "Role fit and keyword gaps identified."],
                  ["Personalize", "Draft ready for human review."],
                ].map(([title, detail]) => (
                  <div key={title} className="rounded-md border border-white/10 bg-white/[0.025] p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-sm font-medium text-white">{title}</p>
                        <p className="mt-1 text-sm leading-6 text-zinc-500">{detail}</p>
                      </div>
                      <span className="mt-1 h-2 w-2 rounded-full bg-zinc-300" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <Link href="#features" className="sr-only">
            Skip to features
          </Link>
        </div>
      </div>
    </section>
  );
}