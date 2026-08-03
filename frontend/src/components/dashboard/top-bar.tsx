"use client";

import { useRef, useState, useEffect } from "react";
import { Bell, LogOut, Menu, User as UserIcon } from "lucide-react";

import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/use-auth";
import { useSidebarStore } from "@/store/sidebar";
import { Button } from "@/components/ui/button";

export function TopBar() {
  const { user, logout } = useAuth();
  const { openMobile } = useSidebarStore();
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node)
      ) {
        setIsProfileOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const initials = user?.full_name
    ? user.full_name
        .split(" ")
        .map((w) => w[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : user?.email?.[0]?.toUpperCase() || "?";

  return (
    <header
      className={cn(
        "sticky top-0 z-20 flex h-14 items-center gap-4 border-b border-white/10 bg-zinc-950/80 px-4 backdrop-blur-xl transition-all duration-200 sm:px-6",
        "lg:pl-6 lg:pr-6",
      )}
    >
      {/* Mobile hamburger */}
      <Button
        variant="ghost"
        size="icon"
        onClick={openMobile}
        className="text-zinc-400 hover:text-white lg:hidden"
        aria-label="Open navigation"
      >
        <Menu className="size-5" />
      </Button>

      {/* Spacer pushes right-side items to the end */}
      <div className="flex-1" />

      {/* Notification placeholder */}
      <Button
        variant="ghost"
        size="icon"
        className="relative text-zinc-400 hover:text-white"
        aria-label="Notifications"
      >
        <Bell className="size-4" />
        <span className="absolute right-1.5 top-1.5 size-1.5 rounded-full bg-blue-500" />
      </Button>

      {/* Profile dropdown */}
      <div ref={dropdownRef} className="relative">
        <button
          onClick={() => setIsProfileOpen(!isProfileOpen)}
          className="flex items-center gap-2 rounded-md px-2 py-1 transition-colors hover:bg-white/[0.06]"
          aria-expanded={isProfileOpen}
          aria-haspopup="true"
        >
          <span className="flex size-7 items-center justify-center rounded-full bg-white/10 text-xs font-medium text-white">
            {initials}
          </span>
          <span className="hidden text-sm text-zinc-300 md:block">
            {user?.full_name || user?.email || "Account"}
          </span>
        </button>

        {isProfileOpen && (
          <div className="absolute right-0 top-full mt-2 w-56 overflow-hidden rounded-lg border border-white/10 bg-zinc-900 shadow-xl">
            {/* User info */}
            <div className="border-b border-white/10 px-4 py-3">
              <p className="text-sm font-medium text-white">
                {user?.full_name || "User"}
              </p>
              <p className="truncate text-xs text-zinc-500">{user?.email}</p>
            </div>

            {/* Actions */}
            <div className="p-1">
              <button
                onClick={() => {
                  setIsProfileOpen(false);
                }}
                className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-zinc-400 transition-colors hover:bg-white/[0.06] hover:text-white"
              >
                <UserIcon className="size-4" />
                Profile
              </button>
              <button
                onClick={() => {
                  setIsProfileOpen(false);
                  logout();
                }}
                className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-zinc-400 transition-colors hover:bg-white/[0.06] hover:text-red-400"
              >
                <LogOut className="size-4" />
                Sign out
              </button>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
