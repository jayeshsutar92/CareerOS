import { api } from "./api";
import {
  ContactListResponse,
  ContactListParams,
  ContactDiscoveryRequest,
  ContactDiscoveryResponse,
  ContactRead,
} from "@/types/contact";

export const contactService = {
  async getContacts(params?: ContactListParams): Promise<ContactListResponse> {
    const { data } = await api.get<ContactListResponse>("/contacts", { params });
    return data;
  },

  async discoverContacts(
    request: ContactDiscoveryRequest,
  ): Promise<ContactDiscoveryResponse> {
    const { data } = await api.post<ContactDiscoveryResponse>("/contacts/discover", request);
    return data;
  },

  async getContact(id: string): Promise<ContactRead> {
    const { data } = await api.get<ContactRead>(`/contacts/${id}`);
    return data;
  },

  async deleteContact(id: string): Promise<void> {
    await api.delete(`/contacts/${id}`);
  },
};
