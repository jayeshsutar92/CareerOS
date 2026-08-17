import { api } from "./api";
import type {
  EmailDeliveryResponse,
  EmailScheduleRequest,
  ScheduledEmailsListResponse,
} from "@/types/scheduler";

export const schedulerService = {
  /** Schedule or send now */
  async scheduleEmail(
    emailId: string,
    request: EmailScheduleRequest,
  ): Promise<EmailDeliveryResponse> {
    const { data } = await api.post<EmailDeliveryResponse>(
      `/emails/${emailId}/schedule`,
      request,
    );
    return data;
  },

  /** Cancel a scheduled email */
  async cancelEmail(emailId: string): Promise<EmailDeliveryResponse> {
    const { data } = await api.post<EmailDeliveryResponse>(
      `/emails/${emailId}/cancel`,
    );
    return data;
  },

  /** Get delivery status of a single email */
  async getDeliveryStatus(emailId: string): Promise<EmailDeliveryResponse> {
    const { data } = await api.get<EmailDeliveryResponse>(
      `/emails/${emailId}/delivery-status`,
    );
    return data;
  },

  /** List all scheduled emails */
  async listScheduledEmails(): Promise<ScheduledEmailsListResponse> {
    const { data } = await api.get<ScheduledEmailsListResponse>(
      "/emails/scheduled",
    );
    return data;
  },

  /** Delete an email */
  async deleteEmail(emailId: string): Promise<void> {
    await api.delete(`/emails/${emailId}`);
  },
};
