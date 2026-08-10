"use client";

import { useState } from "react";
import { format } from "date-fns";
import { Calendar, Clock, Send } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useScheduleEmail } from "@/hooks/use-scheduler";
import { toast } from "sonner";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface ScheduleEmailDialogProps {
  emailId: string;
  trigger?: React.ReactNode;
  onSuccess?: () => void;
}

export function ScheduleEmailDialog({ emailId, trigger, onSuccess }: ScheduleEmailDialogProps) {
  const [open, setOpen] = useState(false);
  const [dateStr, setDateStr] = useState("");
  const [timeStr, setTimeStr] = useState("");
  const [timezone, setTimezone] = useState(Intl.DateTimeFormat().resolvedOptions().timeZone);
  
  const scheduleEmail = useScheduleEmail();

  const handleSendNow = async () => {
    try {
      await scheduleEmail.mutateAsync({
        emailId,
        request: { scheduled_at: null },
      });
      toast.success("Email queued for immediate delivery");
      setOpen(false);
      onSuccess?.();
    } catch (error: any) { // eslint-disable-line @typescript-eslint/no-explicit-any
      toast.error(error?.response?.data?.detail || "Failed to send email");
    }
  };

  const handleSchedule = async () => {
    if (!dateStr || !timeStr) {
      toast.error("Please select both date and time");
      return;
    }

    try {
      // Create a local date string and parse it assuming local timezone (for simplicity in this basic picker)
      // Ideally we'd use the selected timezone, but native datetime inputs use the system's local time.
      const datetimeLocalStr = `${dateStr}T${timeStr}:00`;
      const dateObj = new Date(datetimeLocalStr);
      
      // If the selected timezone differs from local, a proper timezone library like date-fns-tz would adjust it.
      // We pass the ISO string which includes the browser's local timezone offset.
      const scheduled_at = dateObj.toISOString();
      
      await scheduleEmail.mutateAsync({
        emailId,
        request: { scheduled_at },
      });
      toast.success(`Email scheduled for ${format(dateObj, "PPp")}`);
      setOpen(false);
      onSuccess?.();
    } catch (error: any) { // eslint-disable-line @typescript-eslint/no-explicit-any
      toast.error(error?.response?.data?.detail || "Failed to schedule email");
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="outline" className="gap-2">
            <Calendar className="h-4 w-4" />
            Schedule
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px] bg-zinc-950 border-white/10 text-white">
        <DialogHeader>
          <DialogTitle>Schedule Delivery</DialogTitle>
          <DialogDescription className="text-zinc-400">
            Choose when to send this email. Send it immediately or schedule it for a later date.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="date" className="text-zinc-300">Date</Label>
              <Input
                id="date"
                type="date"
                value={dateStr}
                onChange={(e) => setDateStr(e.target.value)}
                min={format(new Date(), "yyyy-MM-dd")}
                className="bg-black/50 border-white/10 text-white [color-scheme:dark]"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="time" className="text-zinc-300">Time</Label>
              <Input
                id="time"
                type="time"
                value={timeStr}
                onChange={(e) => setTimeStr(e.target.value)}
                className="bg-black/50 border-white/10 text-white [color-scheme:dark]"
              />
            </div>
          </div>
          
          <div className="grid gap-2">
            <Label htmlFor="timezone" className="text-zinc-300">Timezone</Label>
            <Select value={timezone} onValueChange={setTimezone}>
              <SelectTrigger className="bg-black/50 border-white/10">
                <SelectValue placeholder="Select timezone" />
              </SelectTrigger>
              <SelectContent className="bg-zinc-950 border-white/10">
                <SelectItem value={Intl.DateTimeFormat().resolvedOptions().timeZone}>
                  {Intl.DateTimeFormat().resolvedOptions().timeZone} (Local)
                </SelectItem>
                <SelectItem value="America/New_York">America/New_York (ET)</SelectItem>
                <SelectItem value="America/Chicago">America/Chicago (CT)</SelectItem>
                <SelectItem value="America/Denver">America/Denver (MT)</SelectItem>
                <SelectItem value="America/Los_Angeles">America/Los_Angeles (PT)</SelectItem>
                <SelectItem value="Europe/London">Europe/London (GMT/BST)</SelectItem>
                <SelectItem value="Europe/Paris">Europe/Paris (CET/CEST)</SelectItem>
                <SelectItem value="Asia/Tokyo">Asia/Tokyo (JST)</SelectItem>
                <SelectItem value="Australia/Sydney">Australia/Sydney (AEST/AEDT)</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-zinc-500 mt-1">
              Currently using local browser time for parsing.
            </p>
          </div>
        </div>

        <DialogFooter className="flex-col sm:flex-row gap-2 sm:justify-between">
          <Button
            type="button"
            variant="secondary"
            className="w-full sm:w-auto gap-2 bg-blue-600 hover:bg-blue-700 text-white border-0"
            onClick={handleSendNow}
            disabled={scheduleEmail.isPending}
          >
            <Send className="h-4 w-4" />
            Send Now
          </Button>
          <div className="flex gap-2 w-full sm:w-auto">
            <Button
              type="button"
              variant="ghost"
              className="w-full sm:w-auto hover:bg-white/5"
              onClick={() => setOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              onClick={handleSchedule}
              disabled={scheduleEmail.isPending || !dateStr || !timeStr}
              className="w-full sm:w-auto gap-2"
            >
              <Clock className="h-4 w-4" />
              Schedule
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
