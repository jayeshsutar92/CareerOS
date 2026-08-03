"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { X } from "lucide-react";

import { cn } from "@/lib/utils";
import { navigation } from "@/lib/navigation";
import { useSidebarStore } from "@/store/sidebar";
import { Button } from "@/components/ui/button";

export function MobileDrawer() {
  const pathname = usePathname();
  const { isMobileOpen, closeMobile } = useSidebarStore();

  // Close on route change
  useEffect(() => {
    closeMobile();
  }, [pathname, closeMobile]);

  // Lock body scroll when open
  useEffect(() => {
    if (isMobileOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isMobileOpen]);

  return (
    <>
      {/* Backdrop */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={closeMobile}
          aria-hidden="true"
        />
      )}

      {/* Drawer */}
      <div
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-white/10 bg-zinc-950 transition-transform duration-200 lg:hidden",
          isMobileOpen ? "translate-x-0" : "-translate-x-full",
        )}
        role="dialog"
        aria-modal="true"
        aria-label="Mobile navigation"
      >
        {/* Header */}
        <div className="flex h-14 items-center justify-between border-b border-white/10 px-4">
          <Link
            href="/dashboard"
            className="flex items-center gap-2.5"
            onClick={closeMobile}
          >
            <span className="flex size-8 shrink-0 items-center justify-center rounded-md border border-white/10 bg-white text-sm font-semibold text-black">
              C
            </span>
            <span className="text-sm font-semibold tracking-wide text-white">
              CareerOS
            </span>
          </Link>
          <Button
            variant="ghost"
            size="icon"
            onClick={closeMobile}
            className="text-zinc-500 hover:text-white"
            aria-label="Close navigation"
          >
            <X className="size-4" />
          </Button>
        </div>

        {/* Navigation */}
        <nav
          aria-label="Mobile navigation"
          className="flex-1 space-y-1 overflow-y-auto px-2 py-3"
        >
          {navigation.map((item) => {
            const isActive =
              item.href === "/dashboard"
                ? pathname === "/dashboard"
                : pathname.startsWith(item.href);

            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={closeMobile}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-white/10 text-white"
                    : "text-zinc-400 hover:bg-white/[0.06] hover:text-white",
                )}
              >
                <item.icon aria-hidden="true" className="size-4 shrink-0" />
                <span>{item.label}</span>
                {item.badge && (
                  <span className="ml-auto rounded-full bg-white/10 px-2 py-0.5 text-xs text-zinc-300">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
      </div>
    </>
  );
}
