// ── Types for Email Delivery / Scheduler ──────────────────────────────────

export type EmailDeliveryStatus =
  | "draft"
  | "scheduled"
  | "sending"
  | "sent"
  | "failed"
  | "cancelled";

export interface EmailDeliveryStatusRead {
  id: string;
  subject: string;
  status: EmailDeliveryStatus;
  scheduled_at: string | null;
  started_at: string | null;
  sent_at: string | null;
  error_message: string | null;
  task_id: string | null;
}

export interface EmailDeliveryResponse {
  status: string;
  data: EmailDeliveryStatusRead | null;
}

export interface EmailScheduleRequest {
  scheduled_at: string | null; // ISO datetime string, null = send now
}

export interface ScheduledEmailsListResponse {
  status: string;
  data: EmailDeliveryStatusRead[];
}
