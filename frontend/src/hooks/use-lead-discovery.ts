import { useMutation } from "@tanstack/react-query";
import { leadDiscoveryService, LeadDiscoveryRequest } from "@/services/lead-discovery";

export function useDiscoverLeads() {
  return useMutation({
    mutationFn: (request: LeadDiscoveryRequest) =>
      leadDiscoveryService.discoverLeads(request),
  });
}
