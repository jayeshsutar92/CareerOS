import { useMutation, useQueryClient } from "@tanstack/react-query";
import { emailService } from "@/services/email";
import { EmailPersonalizationRequest } from "@/types/email";

export function useGenerateEmail() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (request: EmailPersonalizationRequest) => emailService.generate(request),
    onSuccess: () => {
      // Invalidate any email drafts list if exists in future
      queryClient.invalidateQueries({ queryKey: ["email-personalization"] });
    },
  });
}
