"use client";

import { useState, useMemo } from "react";
import { format } from "date-fns";
import { Play, XCircle, RefreshCw, AlertCircle, Clock, Search, Filter } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useScheduledEmails, useCancelEmail, useScheduleEmail } from "@/hooks/use-scheduler";
import { EmailDeliveryStatusRead } from "@/types/scheduler";
import { toast } from "sonner";
import { EmptyState } from "@/components/dashboard/empty-state";

export function ScheduledEmailsTable() {
  const { data, isLoading, isError, refetch } = useScheduledEmails();
  const cancelEmail = useCancelEmail();
  const scheduleEmail = useScheduleEmail();

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [page, setPage] = useState(1);
  const pageSize = 10;

  const handleCancel = async (id: string) => {
    if (!confirm("Are you sure you want to cancel this scheduled email?")) return;
    try {
      await cancelEmail.mutateAsync(id);
      toast.success("Email cancelled successfully");
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Failed to cancel email");
    }
  };

  const handleRetry = async (id: string) => {
    if (!confirm("Are you sure you want to retry sending this email?")) return;
    try {
      await scheduleEmail.mutateAsync({ emailId: id, request: { scheduled_at: null } });
      toast.success("Email queued for sending");
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Failed to retry email");
    }
  };

  const filteredData = useMemo(() => {
    if (!data?.data) return [];
    return data.data.filter((email) => {
      const matchesSearch = email.subject.toLowerCase().includes(search.toLowerCase());
      const matchesStatus = statusFilter === "all" || email.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [data, search, statusFilter]);

  const paginatedData = useMemo(() => {
    const start = (page - 1) * pageSize;
    return filteredData.slice(start, start + pageSize);
  }, [filteredData, page, pageSize]);

  const totalPages = Math.ceil(filteredData.length / pageSize) || 1;

  if (isLoading) {
    return <div className="p-8 text-center text-zinc-400">Loading emails...</div>;
  }

  if (isError || !data) {
    return <div className="p-8 text-center text-red-400">Failed to load emails.</div>;
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "scheduled":
        return <Badge variant="secondary" className="bg-blue-500/10 text-blue-400">Scheduled</Badge>;
      case "sending":
        return <Badge variant="secondary" className="bg-yellow-500/10 text-yellow-400">Sending</Badge>;
      case "sent":
        return <Badge variant="secondary" className="bg-emerald-500/10 text-emerald-400">Sent</Badge>;
      case "failed":
        return <Badge variant="destructive" className="bg-red-500/10 text-red-400">Failed</Badge>;
      case "cancelled":
        return <Badge variant="outline" className="text-zinc-400">Cancelled</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row justify-between gap-4">
        <div className="flex items-center gap-2 flex-1">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-zinc-500" />
            <Input
              placeholder="Search subjects..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              className="pl-9 bg-black/50 border-white/10"
            />
          </div>
          <Select value={statusFilter} onValueChange={(val) => { setStatusFilter(val); setPage(1); }}>
            <SelectTrigger className="w-[180px] bg-black/50 border-white/10">
              <Filter className="mr-2 h-4 w-4 text-zinc-500" />
              <SelectValue placeholder="Filter Status" />
            </SelectTrigger>
            <SelectContent className="bg-zinc-950 border-white/10">
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="scheduled">Scheduled</SelectItem>
              <SelectItem value="sending">Sending</SelectItem>
              <SelectItem value="sent">Sent</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
              <SelectItem value="cancelled">Cancelled</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>
      
      {filteredData.length === 0 ? (
        <EmptyState
          icon={Clock}
          title="No emails found"
          description={search || statusFilter !== "all" ? "Try adjusting your filters." : "You have no emails matching the current criteria."}
        />
      ) : (
        <div className="rounded-md border border-white/10 bg-black/20">
          <Table>
            <TableHeader>
              <TableRow className="border-white/10 hover:bg-transparent">
                <TableHead className="text-zinc-400">Subject</TableHead>
                <TableHead className="text-zinc-400">Status</TableHead>
                <TableHead className="text-zinc-400">Scheduled For</TableHead>
                <TableHead className="text-zinc-400">Sent At</TableHead>
                <TableHead className="text-right text-zinc-400">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedData.map((email: EmailDeliveryStatusRead) => (
                <TableRow key={email.id} className="border-white/10 hover:bg-white/[0.02]">
                  <TableCell className="font-medium text-zinc-200">
                    <div className="max-w-[300px] truncate" title={email.subject}>
                      {email.subject || "No Subject"}
                    </div>
                    {email.error_message && (
                      <div className="mt-1 flex items-center text-xs text-red-400">
                        <AlertCircle className="mr-1 h-3 w-3" />
                        <span className="truncate max-w-[250px]" title={email.error_message}>
                          {email.error_message}
                        </span>
                      </div>
                    )}
                  </TableCell>
                  <TableCell>{getStatusBadge(email.status)}</TableCell>
                  <TableCell className="text-zinc-400 text-sm">
                    {email.scheduled_at
                      ? format(new Date(email.scheduled_at), "MMM d, yyyy h:mm a")
                      : "-"}
                  </TableCell>
                  <TableCell className="text-zinc-400 text-sm">
                    {email.sent_at
                      ? format(new Date(email.sent_at), "MMM d, yyyy h:mm a")
                      : "-"}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      {email.status === "scheduled" && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 text-zinc-400 hover:text-red-400"
                          onClick={() => handleCancel(email.id)}
                          disabled={cancelEmail.isPending}
                        >
                          <XCircle className="mr-2 h-4 w-4" />
                          Cancel
                        </Button>
                      )}
                      {(email.status === "failed" || email.status === "cancelled") && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 text-zinc-400 hover:text-blue-400"
                          onClick={() => handleRetry(email.id)}
                          disabled={scheduleEmail.isPending}
                        >
                          <Play className="mr-2 h-4 w-4" />
                          Retry
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          
          <div className="flex items-center justify-between px-4 py-4 border-t border-white/10">
            <div className="text-sm text-zinc-400">
              Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, filteredData.length)} of {filteredData.length} entries
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                Next
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
