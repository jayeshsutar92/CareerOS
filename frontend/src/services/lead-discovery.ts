import { api } from "./api";
import { ContactRead } from "../types/contact";

export interface LeadDiscoveryRequest {
  jobRole?: string;
  location: string;
  workMode: string;
  batchSize: number;
}

export interface LeadDiscoveryResponse {
  status: string;
  task_id: string | null;
}

export interface TaskStatusResponse {
  status: string;
  error?: string | null;
  result?: LeadDiscoveryTaskResult | null;
}

export interface DiscoveredCompany {
  name: string;
  url: string;
  contacts_count: number;
  company_score?: number;
  contacts?: ContactRead[];
}

export interface LeadDiscoveryTaskOutput {
  status?: string;
  error?: string;
  location?: string;
  contacts_discovered?: number;
  discovered_companies?: DiscoveredCompany[];
  processed_contact_ids?: string[];
}

interface LeadDiscoveryTaskResult {
  results?: Array<{ output?: LeadDiscoveryTaskOutput }>;
  output?: LeadDiscoveryTaskOutput;
  status?: string;
  error?: string;
  location?: string;
  contacts_discovered?: number;
  discovered_companies?: DiscoveredCompany[];
  processed_contact_ids?: string[];
}

/** Unwrap the worker's `result.results[0].output` response shape. */
export function getLeadDiscoveryTaskOutput(
  result: LeadDiscoveryTaskResult | null | undefined,
): LeadDiscoveryTaskOutput | undefined {
  if (!result) return undefined;
  return result.results?.[0]?.output ?? result.output ?? result;
}

export const leadDiscoveryService = {
  discoverLeads: async (request: LeadDiscoveryRequest): Promise<LeadDiscoveryResponse> => {
    // Map to backend schema which is snake_case
    const payload: any = {
      location: request.location,
      work_mode: request.workMode,
      batch_size: request.batchSize,
    };
    if (request.jobRole && request.jobRole.trim() !== "") {
      payload.job_role = request.jobRole.trim();
    }
    const { data } = await api.post("/lead-discovery", payload);
    return data;
  },
  
  getTaskStatus: async (taskId: string): Promise<TaskStatusResponse> => {
    const { data } = await api.get(`/tasks/${taskId}`);
    return data;
  },

  cancelTask: async (taskId: string): Promise<void> => {
    await api.post(`/tasks/${taskId}/cancel`);
  }
};
