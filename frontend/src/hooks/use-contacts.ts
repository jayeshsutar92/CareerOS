import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { contactService } from "@/services/contacts";
import { ContactListParams, ContactDiscoveryRequest } from "@/types/contact";

export function useContacts(params: ContactListParams = {}) {
  return useQuery({
    queryKey: ["contacts", params],
    queryFn: () => contactService.getContacts(params),
    placeholderData: (previousData) => previousData,
  });
}

export function useContact(id: string) {
  return useQuery({
    queryKey: ["contacts", id],
    queryFn: () => contactService.getContact(id),
    enabled: !!id,
  });
}

export function useDiscoverContacts() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: ContactDiscoveryRequest) =>
      contactService.discoverContacts(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contacts"] });
    },
  });
}
