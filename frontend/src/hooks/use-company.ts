import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { companyService } from "@/services/company";
import { CompanyListParams, CompanyIntelligenceRequest } from "@/types/company";

export function useCompanyIntelligenceList(params: CompanyListParams = {}) {
  return useQuery({
    queryKey: ["company-intelligence", params],
    queryFn: () => companyService.getCompanyIntelligenceList(params),
    placeholderData: (previousData) => previousData,
    refetchInterval: 5000,
  });
}

export function useCompanyIntelligence(id: string) {
  return useQuery({
    queryKey: ["company-intelligence", id],
    queryFn: () => companyService.getCompanyIntelligence(id),
    enabled: !!id,
    refetchInterval: (query) => {
      // Auto-refresh if status is processing/queued
      const status = query.state.data?.status;
      if (status === "processing" || status === "queued") {
        return 3000;
      }
      return false;
    },
  });
}

export function useAnalyzeCompany() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: CompanyIntelligenceRequest) =>
      companyService.analyzeCompany(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["company-intelligence"] });
    },
  });
}

export function useRefreshCompanyIntelligence() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => companyService.refreshCompanyIntelligence(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ["company-intelligence"] });
      queryClient.invalidateQueries({ queryKey: ["company-intelligence", id] });
    },
  });
}
