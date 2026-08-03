import type { Metadata } from "next";
import "./globals.css";
import { QueryProvider } from "@/providers/query-provider";
import { AuthGuard } from "@/providers/auth-guard";

export const metadata: Metadata = {
  title: "CareerOS - Your AI Career Operating System",
  description:
    "Discover opportunities, research companies, generate personalized outreach, and manage your job search from one intelligent workspace.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark h-full scroll-smooth antialiased">
      <body className="flex min-h-full flex-col">
        <QueryProvider>
          <AuthGuard>{children}</AuthGuard>
        </QueryProvider>
      </body>
    </html>
  );
}