import type { Metadata } from "next";
import { RegisterForm } from "@/components/auth/register-form";

export const metadata: Metadata = {
  title: "Create Account – CareerOS",
  description: "Create your CareerOS account and start managing your career.",
};

export default function RegisterPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <RegisterForm />
    </div>
  );
}
