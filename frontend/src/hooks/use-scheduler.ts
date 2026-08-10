import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { schedulerService } from "@/services/scheduler";
import { EmailScheduleRequest } from "@/types/scheduler";

export function useScheduledEmails() {
  return useQuery({
    queryKey: ["scheduled-emails"],
    queryFn: () => schedulerService.listScheduledEmails(),
    refetchInterval: 5000,
  });
}

export function useEmailDeliveryStatus(emailId: string) {
  return useQuery({
    queryKey: ["email-delivery-status", emailId],
    queryFn: () => schedulerService.getDeliveryStatus(emailId),
    enabled: !!emailId,
    refetchInterval: (query) => {
      // Refetch every 5 seconds if status is 'sending' or 'scheduled' (if we want live updates)
      const status = query.state.data?.data?.status;
      if (status === "sending" || status === "scheduled") {
        return 5000;
      }
      return false;
    },
  });
}

export function useScheduleEmail() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      emailId,
      request,
    }: {
      emailId: string;
      request: EmailScheduleRequest;
    }) => schedulerService.scheduleEmail(emailId, request),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["scheduled-emails"] });
      queryClient.invalidateQueries({
        queryKey: ["email-delivery-status", variables.emailId],
      });
    },
  });
}

export function useCancelEmail() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (emailId: string) => schedulerService.cancelEmail(emailId),
    onSuccess: (_, emailId) => {
      queryClient.invalidateQueries({ queryKey: ["scheduled-emails"] });
      queryClient.invalidateQueries({
        queryKey: ["email-delivery-status", emailId],
      });
    },
  });
}
