import { api } from "./api";
import {
  EmailPersonalizationResponse,
  EmailPersonalizationRequest,
} from "@/types/email";

export const emailService = {
  async generate(request: EmailPersonalizationRequest): Promise<EmailPersonalizationResponse> {
    const { data } = await api.post<EmailPersonalizationResponse>(
      "/email-personalization/generate",
      request,
    );
    return data;
  },
};
