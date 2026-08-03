import type { Metadata } from "next";
import { Suspense } from "react";
import { ResetPasswordForm } from "@/components/auth/reset-password-form";

export const metadata: Metadata = {
  title: "Reset Password – CareerOS",
  description: "Set a new password for your CareerOS account.",
};

export default function ResetPasswordPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Suspense
        fallback={
          <div className="text-sm text-zinc-500">Loading…</div>
        }
      >
        <ResetPasswordForm />
      </Suspense>
    </div>
  );
}
