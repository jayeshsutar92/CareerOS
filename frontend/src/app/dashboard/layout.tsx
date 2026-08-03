"use client";

import { Loader2 } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { useSidebarStore } from "@/store/sidebar";
import { Sidebar } from "@/components/dashboard/sidebar";
import { MobileDrawer } from "@/components/dashboard/mobile-drawer";
import { TopBar } from "@/components/dashboard/top-bar";
import { cn } from "@/lib/utils";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isLoading, isAuthenticated } = useAuth();
  const { isCollapsed } = useSidebarStore();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="size-6 animate-spin text-zinc-500" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null; // AuthGuard handles redirect
  }

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <MobileDrawer />

      <div
        className={cn(
          "flex flex-col transition-all duration-200",
          isCollapsed ? "lg:pl-16" : "lg:pl-60",
        )}
      >
        <TopBar />
        <main className="flex-1 px-4 py-6 sm:px-6">{children}</main>
      </div>
    </div>
  );
}
