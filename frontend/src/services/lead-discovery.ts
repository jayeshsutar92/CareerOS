import { api } from "./api";

export interface LeadDiscoveryRequest {
  location: string;
  workMode: string;
  batchSize: number;
}

export interface LeadDiscoveryResponse {
  status: string;
  task_id: string | null;
}

export const leadDiscoveryService = {
  discoverLeads: async (request: LeadDiscoveryRequest): Promise<LeadDiscoveryResponse> => {
    // Map to backend schema which is snake_case
    const payload = {
      location: request.location,
      work_mode: request.workMode,
      batch_size: request.batchSize,
    };
    const { data } = await api.post("/lead-discovery", payload);
    return data;
  },
};
