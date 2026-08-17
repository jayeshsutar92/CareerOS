"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { PageHeader } from "@/components/dashboard/page-header";
import { ShieldCheck, Users, Building2, Contact, Mail, Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useSystemStats, useAdminUsers, useDeleteUser, useAdminCompanies, useDeleteAdminCompany, useAdminContacts, useDeleteAdminContact, useAdminEmails, useDeleteAdminEmail, useAdminTasks, useDeleteAdminTask } from "@/hooks/use-admin";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { format } from "date-fns";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function AdminDashboardPage() {
  const { user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (user && !user.is_admin) {
      router.push("/dashboard");
    }
  }, [user, router]);

  if (!user || !user.is_admin) {
    return null; // Will redirect
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Admin Dashboard"
        description="Platform administration and data management."
        icon={ShieldCheck}
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Admin" },
        ]}
      />

      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="bg-zinc-900 border border-zinc-800 flex flex-wrap h-auto">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="users">Users</TabsTrigger>
          <TabsTrigger value="companies">Companies</TabsTrigger>
          <TabsTrigger value="contacts">Contacts</TabsTrigger>
          <TabsTrigger value="emails">Emails</TabsTrigger>
          <TabsTrigger value="tasks">Tasks</TabsTrigger>
        </TabsList>
        <TabsContent value="overview" className="mt-6">
          <SystemStatsOverview />
        </TabsContent>
        <TabsContent value="users" className="mt-6">
          <AdminUsersTable />
        </TabsContent>
        <TabsContent value="companies" className="mt-6">
          <AdminCompaniesTable />
        </TabsContent>
        <TabsContent value="contacts" className="mt-6">
          <AdminContactsTable />
        </TabsContent>
        <TabsContent value="emails" className="mt-6">
          <AdminEmailsTable />
        </TabsContent>
        <TabsContent value="tasks" className="mt-6">
          <AdminTasksTable />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function SystemStatsOverview() {
  const { data, isLoading } = useSystemStats();

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i} className="bg-zinc-950 border-zinc-800">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 w-4" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-8 w-16" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (!data) return null;

  const stats = [
    { title: "Total Users", value: data.users, icon: Users, color: "text-blue-500" },
    { title: "Companies", value: data.companies, icon: Building2, color: "text-green-500" },
    { title: "Contacts", value: data.contacts, icon: Contact, color: "text-purple-500" },
    { title: "Emails Drafted", value: data.emails, icon: Mail, color: "text-orange-500" },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {stats.map((stat, i) => (
        <Card key={i} className="bg-zinc-950 border-zinc-800">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-zinc-400">
              {stat.title}
            </CardTitle>
            <stat.icon className={`h-4 w-4 ${stat.color}`} />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">{stat.value}</div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function AdminUsersTable() {
  const { data: users, isLoading } = useAdminUsers();
  const deleteMutation = useDeleteUser();
  const { user: currentUser } = useAuth();

  if (isLoading) {
    return (
      <div className="border border-zinc-800 rounded-md bg-zinc-950 p-4">
        <Skeleton className="h-8 w-full mb-4" />
        <Skeleton className="h-8 w-full mb-4" />
        <Skeleton className="h-8 w-full" />
      </div>
    );
  }

  return (
    <div className="border border-zinc-800 rounded-md bg-zinc-950">
      <Table>
        <TableHeader>
          <TableRow className="border-zinc-800 hover:bg-transparent">
            <TableHead className="text-zinc-400">Email</TableHead>
            <TableHead className="text-zinc-400">Status</TableHead>
            <TableHead className="text-zinc-400">Role</TableHead>
            <TableHead className="text-zinc-400">Created</TableHead>
            <TableHead className="text-right text-zinc-400">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {users?.map((u) => (
            <TableRow key={u.id} className="border-zinc-800 hover:bg-zinc-900/50">
              <TableCell className="font-medium text-white">
                {u.email}
              </TableCell>
              <TableCell>
                {u.is_active ? (
                  <span className="text-green-500 text-xs">Active</span>
                ) : (
                  <span className="text-red-500 text-xs">Inactive</span>
                )}
              </TableCell>
              <TableCell>
                {u.is_admin ? (
                  <span className="text-purple-500 text-xs font-semibold">Admin</span>
                ) : (
                  <span className="text-zinc-400 text-xs">User</span>
                )}
              </TableCell>
              <TableCell className="text-zinc-500 text-sm">
                {format(new Date(u.created_at), "MMM d, yyyy")}
              </TableCell>
              <TableCell className="text-right">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-red-500/70 hover:text-red-400 hover:bg-red-950/30"
                  disabled={u.id === currentUser?.id || deleteMutation.isPending}
                  onClick={() => {
                    if (window.confirm(`Are you sure you want to delete user ${u.email}?`)) {
                      deleteMutation.mutate(u.id);
                    }
                  }}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function AdminCompaniesTable() {
  const { data: companies, isLoading } = useAdminCompanies();
  const deleteMutation = useDeleteAdminCompany();

  if (isLoading) {
    return <Skeleton className="h-[400px] w-full rounded-md border border-zinc-800 bg-zinc-950" />;
  }

  return (
    <div className="border border-zinc-800 rounded-md bg-zinc-950">
      <Table>
        <TableHeader>
          <TableRow className="border-zinc-800 hover:bg-transparent">
            <TableHead className="text-zinc-400">Company Name</TableHead>
            <TableHead className="text-zinc-400">Status</TableHead>
            <TableHead className="text-zinc-400">Created</TableHead>
            <TableHead className="text-right text-zinc-400">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {companies?.map((c) => (
            <TableRow key={c.id} className="border-zinc-800 hover:bg-zinc-900/50">
              <TableCell className="font-medium text-white">{c.company_name}</TableCell>
              <TableCell>
                <span className="text-xs text-zinc-400 capitalize">{c.status}</span>
              </TableCell>
              <TableCell className="text-zinc-500 text-sm">
                {format(new Date(c.created_at), "MMM d, yyyy")}
              </TableCell>
              <TableCell className="text-right">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-red-500/70 hover:text-red-400 hover:bg-red-950/30"
                  disabled={deleteMutation.isPending}
                  onClick={() => {
                    if (window.confirm(`Delete company ${c.company_name}?`)) {
                      deleteMutation.mutate(c.id);
                    }
                  }}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function AdminContactsTable() {
  const { data: contacts, isLoading } = useAdminContacts();
  const deleteMutation = useDeleteAdminContact();

  if (isLoading) {
    return <Skeleton className="h-[400px] w-full rounded-md border border-zinc-800 bg-zinc-950" />;
  }

  return (
    <div className="border border-zinc-800 rounded-md bg-zinc-950">
      <Table>
        <TableHeader>
          <TableRow className="border-zinc-800 hover:bg-transparent">
            <TableHead className="text-zinc-400">Name</TableHead>
            <TableHead className="text-zinc-400">Created</TableHead>
            <TableHead className="text-right text-zinc-400">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {contacts?.map((c) => (
            <TableRow key={c.id} className="border-zinc-800 hover:bg-zinc-900/50">
              <TableCell className="font-medium text-white">{c.name}</TableCell>
              <TableCell className="text-zinc-500 text-sm">
                {format(new Date(c.created_at), "MMM d, yyyy")}
              </TableCell>
              <TableCell className="text-right">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-red-500/70 hover:text-red-400 hover:bg-red-950/30"
                  disabled={deleteMutation.isPending}
                  onClick={() => {
                    if (window.confirm(`Delete contact ${c.name}?`)) {
                      deleteMutation.mutate(c.id);
                    }
                  }}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function AdminEmailsTable() {
  const { data: emails, isLoading } = useAdminEmails();
  const deleteMutation = useDeleteAdminEmail();

  if (isLoading) {
    return <Skeleton className="h-[400px] w-full rounded-md border border-zinc-800 bg-zinc-950" />;
  }

  return (
    <div className="border border-zinc-800 rounded-md bg-zinc-950">
      <Table>
        <TableHeader>
          <TableRow className="border-zinc-800 hover:bg-transparent">
            <TableHead className="text-zinc-400">Subject</TableHead>
            <TableHead className="text-zinc-400">Status</TableHead>
            <TableHead className="text-zinc-400">Created</TableHead>
            <TableHead className="text-right text-zinc-400">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {emails?.map((e) => (
            <TableRow key={e.id} className="border-zinc-800 hover:bg-zinc-900/50">
              <TableCell className="font-medium text-white">{e.subject || "No Subject"}</TableCell>
              <TableCell>
                <span className="text-xs text-zinc-400 capitalize">{e.status}</span>
              </TableCell>
              <TableCell className="text-zinc-500 text-sm">
                {format(new Date(e.created_at), "MMM d, yyyy")}
              </TableCell>
              <TableCell className="text-right">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-red-500/70 hover:text-red-400 hover:bg-red-950/30"
                  disabled={deleteMutation.isPending}
                  onClick={() => {
                    if (window.confirm("Delete this email?")) {
                      deleteMutation.mutate(e.id);
                    }
                  }}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function AdminTasksTable() {
  const { data: tasks, isLoading } = useAdminTasks();
  const deleteMutation = useDeleteAdminTask();

  if (isLoading) {
    return <Skeleton className="h-[400px] w-full rounded-md border border-zinc-800 bg-zinc-950" />;
  }

  return (
    <div className="border border-zinc-800 rounded-md bg-zinc-950">
      <Table>
        <TableHeader>
          <TableRow className="border-zinc-800 hover:bg-transparent">
            <TableHead className="text-zinc-400">Task ID</TableHead>
            <TableHead className="text-zinc-400">User ID</TableHead>
            <TableHead className="text-zinc-400">Status</TableHead>
            <TableHead className="text-right text-zinc-400">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {tasks?.map((t) => (
            <TableRow key={t.id} className="border-zinc-800 hover:bg-zinc-900/50">
              <TableCell className="font-medium text-zinc-300 text-xs font-mono">{t.id}</TableCell>
              <TableCell className="text-zinc-400 text-xs font-mono">{t.user_id}</TableCell>
              <TableCell>
                <span className="text-xs text-zinc-400 capitalize">{t.status}</span>
              </TableCell>
              <TableCell className="text-right">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-red-500/70 hover:text-red-400 hover:bg-red-950/30"
                  disabled={deleteMutation.isPending}
                  onClick={() => {
                    if (window.confirm("Delete this task?")) {
                      deleteMutation.mutate({ userId: t.user_id, taskId: t.id });
                    }
                  }}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
