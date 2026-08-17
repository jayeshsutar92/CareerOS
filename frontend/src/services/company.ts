import { api } from "./api";
import {
  CompanyIntelligenceListResponse,
  CompanyListParams,
  CompanyIntelligenceRequest,
  CompanyIntelligenceResponse,
  CompanyIntelligenceRead,
} from "@/types/company";

export const companyService = {
  async getCompanyIntelligenceList(
    params?: CompanyListParams,
  ): Promise<CompanyIntelligenceListResponse> {
    const { data } = await api.get<CompanyIntelligenceListResponse>(
      "/company-intelligence",
      { params },
    );
    return data;
  },

  async analyzeCompany(
    request: CompanyIntelligenceRequest,
  ): Promise<CompanyIntelligenceResponse> {
    const { data } = await api.post<CompanyIntelligenceResponse>(
      "/company-intelligence/analyze",
      request,
    );
    return data;
  },

  async getCompanyIntelligence(id: string): Promise<CompanyIntelligenceRead> {
    const { data } = await api.get<CompanyIntelligenceRead>(
      `/company-intelligence/${id}`,
    );
    return data;
  },

  async refreshCompanyIntelligence(
    id: string,
  ): Promise<CompanyIntelligenceResponse> {
    const { data } = await api.post<CompanyIntelligenceResponse>(
      `/company-intelligence/${id}/refresh`,
    );
    return data;
  },

  async deleteCompanyIntelligence(id: string): Promise<void> {
    await api.delete(`/company-intelligence/${id}`);
  },
};
