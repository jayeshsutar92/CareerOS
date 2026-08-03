"use client";

import { useCallback } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { authService } from "@/services/auth";
import { useAuthStore } from "@/store/auth";
import type { LoginRequest, RegisterRequest } from "@/types/auth";
import { isAxiosError } from "axios";

/** Extract a human-readable error message from an API error */
function extractErrorMessage(error: unknown): string {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((d) => d.msg).join(", ");
    }
    if (error.response?.status === 401) return "Invalid credentials";
    if (error.response?.status === 409) return "Email already registered";
  }
  return "Something went wrong. Please try again.";
}

export function useAuth() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { setUser, setTokens, clearAuth, isAuthenticated, user, isLoading } =
    useAuthStore();

  // Fetch the current user on mount if a token exists
  const { isLoading: isFetchingUser } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: async () => {
      const user = await authService.getMe();
      setUser(user);
      return user;
    },
    enabled:
      typeof window !== "undefined" &&
      !!localStorage.getItem("access_token"),
    retry: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
    meta: {
      onError: () => {
        clearAuth();
      },
    },
  });

  const loginMutation = useMutation({
    mutationFn: (payload: LoginRequest) => authService.login(payload),
    onSuccess: (data) => {
      setTokens(data.access_token, data.refresh_token);
      setUser(data.user);
      queryClient.setQueryData(["auth", "me"], data.user);
      router.push("/dashboard");
    },
  });

  const registerMutation = useMutation({
    mutationFn: (payload: RegisterRequest) => authService.register(payload),
    onSuccess: (data) => {
      setTokens(data.access_token, data.refresh_token);
      setUser(data.user);
      queryClient.setQueryData(["auth", "me"], data.user);
      router.push("/dashboard");
    },
  });

  const logout = useCallback(async () => {
    try {
      await authService.logout();
    } catch {
      // Swallow – clear local state regardless
    }
    clearAuth();
    queryClient.removeQueries({ queryKey: ["auth"] });
    router.push("/login");
  }, [clearAuth, queryClient, router]);

  return {
    user,
    isAuthenticated,
    isLoading: isLoading || isFetchingUser,
    login: loginMutation.mutateAsync,
    loginError: loginMutation.error
      ? extractErrorMessage(loginMutation.error)
      : null,
    isLoggingIn: loginMutation.isPending,
    register: registerMutation.mutateAsync,
    registerError: registerMutation.error
      ? extractErrorMessage(registerMutation.error)
      : null,
    isRegistering: registerMutation.isPending,
    logout,
    extractErrorMessage,
  };
}
