import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const navigationItems = [
  { label: "Features", href: "#features" },
  { label: "How It Works", href: "#how-it-works" },
  { label: "Pricing", href: "#" },
  { label: "GitHub", href: "#" },
];

export function Navbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-white/10 bg-background/85 backdrop-blur-xl">
      <nav
        aria-label="Main navigation"
        className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8"
      >
        <Link href="/" className="flex items-center gap-2" aria-label="CareerOS home">
          <span className="flex size-8 items-center justify-center rounded-md border border-white/10 bg-white text-sm font-semibold text-black">
            C
          </span>
          <span className="text-sm font-semibold tracking-wide text-white">CareerOS</span>
        </Link>

        <div className="hidden items-center gap-7 md:flex">
          {navigationItems.map((item) => (
            <Link
              key={item.label}
              href={item.href}
              className="text-sm text-zinc-400 transition-colors hover:text-white"
            >
              {item.label}
            </Link>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/login"
            className={cn(
              buttonVariants({ variant: "ghost", size: "lg" }),
              "hidden text-zinc-300 sm:inline-flex",
            )}
          >
            Login
          </Link>
          <Link
            href="/register"
            className={cn(buttonVariants({ size: "lg" }), "bg-white text-black hover:bg-zinc-200")}
          >
            Get Started
            <ArrowRight aria-hidden="true" className="size-4" />
          </Link>
        </div>
      </nav>
    </header>
  );
}