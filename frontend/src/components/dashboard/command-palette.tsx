"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Search, Mail, Building2, Users, Calendar, Settings } from "lucide-react";
import {
  Dialog,
  DialogContent,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const router = useRouter();

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  const runCommand = (command: () => void) => {
    setOpen(false);
    command();
  };

  const routes = [
    { name: "Dashboard", href: "/dashboard", icon: <Building2 className="mr-2 h-4 w-4" /> },
    { name: "Contacts", href: "/dashboard/contacts", icon: <Users className="mr-2 h-4 w-4" /> },
    { name: "Company Intelligence", href: "/dashboard/company-intelligence", icon: <Search className="mr-2 h-4 w-4" /> },
    { name: "Email Personalization", href: "/dashboard/email-personalization", icon: <Mail className="mr-2 h-4 w-4" /> },
    { name: "Scheduler", href: "/dashboard/scheduler", icon: <Calendar className="mr-2 h-4 w-4" /> },
    { name: "Settings", href: "/dashboard/settings", icon: <Settings className="mr-2 h-4 w-4" /> },
  ];

  const filteredRoutes = routes.filter((route) =>
    route.name.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 rounded-md border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-zinc-400 transition-colors hover:bg-white/10"
      >
        <Search className="h-4 w-4" />
        <span className="hidden sm:inline-block">Search...</span>
        <kbd className="pointer-events-none hidden h-5 select-none items-center gap-1 rounded border border-white/10 bg-black/50 px-1.5 font-mono text-[10px] font-medium text-zinc-400 sm:flex">
          <span className="text-xs">⌘</span>K
        </kbd>
      </button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="p-0 overflow-hidden bg-zinc-950 border-white/10 shadow-2xl sm:max-w-xl">
          <div className="flex items-center border-b border-white/10 px-3">
            <Search className="h-4 w-4 text-zinc-500 shrink-0" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Type a command or search..."
              className="border-0 bg-transparent text-white focus-visible:ring-0 shadow-none h-12"
            />
          </div>
          <div className="max-h-80 overflow-y-auto p-2">
            {filteredRoutes.length === 0 ? (
              <p className="p-4 text-center text-sm text-zinc-500">No results found.</p>
            ) : (
              <div className="space-y-1">
                <p className="px-2 pb-2 text-xs font-medium text-zinc-500">Navigation</p>
                {filteredRoutes.map((route) => (
                  <button
                    key={route.href}
                    onClick={() => runCommand(() => router.push(route.href))}
                    className="flex w-full items-center rounded-md px-2 py-2 text-sm text-zinc-300 hover:bg-white/10 hover:text-white"
                  >
                    {route.icon}
                    {route.name}
                  </button>
                ))}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
