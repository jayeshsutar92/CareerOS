"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore } from "@/store/auth";

const PUBLIC_ROUTES = ["/", "/login", "/register", "/forgot-password", "/reset-password"];

export function AuthGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isLoading, hydrate } = useAuthStore();

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (isLoading) return;

    const isPublic = PUBLIC_ROUTES.some(
      (route) => pathname === route || pathname.startsWith("/reset-password"),
    );

    if (!isAuthenticated && !isPublic) {
      router.replace("/login");
    }

    // Redirect authenticated users away from auth pages
    if (
      isAuthenticated &&
      ["/login", "/register", "/forgot-password"].includes(pathname)
    ) {
      router.replace("/dashboard");
    }
  }, [isAuthenticated, isLoading, pathname, router]);

  return <>{children}</>;
}
