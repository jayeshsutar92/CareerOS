"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { cn } from "@/lib/utils";
import { navigation } from "@/lib/navigation";
import { useSidebarStore } from "@/store/sidebar";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";
import { ShieldCheck } from "lucide-react";

export function Sidebar() {
  const pathname = usePathname();
  const { isCollapsed, toggle } = useSidebarStore();
  const { user } = useAuth();

  return (
    <aside
      className={cn(
        "fixed inset-y-0 left-0 z-30 hidden flex-col border-r border-white/10 bg-zinc-950 transition-all duration-200 lg:flex",
        isCollapsed ? "w-16" : "w-60",
      )}
    >
      {/* Logo */}
      <div className="flex h-14 items-center border-b border-white/10 px-4">
        <Link href="/dashboard" className="flex items-center gap-2.5">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-md border border-white/10 bg-white text-sm font-semibold text-black">
            C
          </span>
          {!isCollapsed && (
            <span className="text-sm font-semibold tracking-wide text-white">
              CareerOS
            </span>
          )}
        </Link>
      </div>

      {/* Navigation */}
      <nav aria-label="Sidebar navigation" className="flex-1 space-y-1 px-2 py-3">
        {navigation.map((item) => {
          const isActive =
            item.href === "/dashboard"
              ? pathname === "/dashboard"
              : pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-white/10 text-white"
                  : "text-zinc-400 hover:bg-white/[0.06] hover:text-white",
                isCollapsed && "justify-center px-2",
              )}
              title={isCollapsed ? item.label : undefined}
            >
              <item.icon aria-hidden="true" className="size-4 shrink-0" />
              {!isCollapsed && <span>{item.label}</span>}
              {!isCollapsed && item.badge && (
                <span className="ml-auto rounded-full bg-white/10 px-2 py-0.5 text-xs text-zinc-300">
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}

        {user?.is_admin && (
          <Link
            href="/dashboard/admin"
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              pathname.startsWith("/dashboard/admin")
                ? "bg-white/10 text-white"
                : "text-zinc-400 hover:bg-white/[0.06] hover:text-white",
              isCollapsed && "justify-center px-2",
            )}
            title={isCollapsed ? "Admin Dashboard" : undefined}
          >
            <ShieldCheck aria-hidden="true" className="size-4 shrink-0" />
            {!isCollapsed && <span>Admin Dashboard</span>}
          </Link>
        )}
      </nav>

      {/* Collapse toggle */}
      <div className="border-t border-white/10 p-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={toggle}
          className="w-full text-zinc-500 hover:text-white"
          aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {isCollapsed ? (
            <ChevronRight className="size-4" />
          ) : (
            <ChevronLeft className="size-4" />
          )}
        </Button>
      </div>
    </aside>
  );
}
