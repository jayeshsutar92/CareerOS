import { api } from "@/services/api"

export interface BulkEmailRequest {
  template_id: string
  recipient_ids: string[]
}

export interface BulkEmailResponse {
  task_id: string
}

export const outreachApi = {
  sendBulkEmails: async (payload: BulkEmailRequest): Promise<BulkEmailResponse> => {
    const { data } = await api.post("/outreach/send-bulk", payload)
    return data
  },
}
