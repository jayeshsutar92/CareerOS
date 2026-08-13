import { useMutation, useQueryClient } from "@tanstack/react-query";
import { leadDiscoveryService, LeadDiscoveryRequest } from "@/services/lead-discovery";

export function useDiscoverLeads() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: LeadDiscoveryRequest) =>
      leadDiscoveryService.discoverLeads(request),
  });
}
