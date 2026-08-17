import { api } from "./api";

export interface SystemStats {
  users: number;
  companies: number;
  contacts: number;
  emails: number;
}

export interface AdminUser {
  id: string;
  email: string;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
}

export interface AdminCompany {
  id: string;
  company_name: string;
  status: string;
  user_id: string;
  created_at: string;
}

export interface AdminContact {
  id: string;
  name: string;
  company_id: string;
  user_id: string;
  created_at: string;
}

export interface AdminEmail {
  id: string;
  subject: string;
  status: string;
  user_id: string;
  created_at: string;
}

export interface AdminTask {
  id: string;
  user_id: string;
  status: string;
}

export const adminService = {
  async getStatistics(): Promise<SystemStats> {
    const { data } = await api.get<SystemStats>("/admin/statistics");
    return data;
  },

  async getUsers(): Promise<AdminUser[]> {
    const { data } = await api.get<AdminUser[]>("/admin/users");
    return data;
  },

  async deleteUser(userId: string): Promise<void> {
    await api.delete(`/admin/users/${userId}`);
  },

  async getCompanies(): Promise<AdminCompany[]> {
    const { data } = await api.get<AdminCompany[]>("/admin/companies");
    return data;
  },

  async deleteCompany(companyId: string): Promise<void> {
    await api.delete(`/admin/companies/${companyId}`);
  },

  async getContacts(): Promise<AdminContact[]> {
    const { data } = await api.get<AdminContact[]>("/admin/contacts");
    return data;
  },

  async deleteContact(contactId: string): Promise<void> {
    await api.delete(`/admin/contacts/${contactId}`);
  },

  async getEmails(): Promise<AdminEmail[]> {
    const { data } = await api.get<AdminEmail[]>("/admin/emails");
    return data;
  },

  async deleteEmail(emailId: string): Promise<void> {
    await api.delete(`/admin/emails/${emailId}`);
  },

  async getTasks(): Promise<AdminTask[]> {
    const { data } = await api.get<AdminTask[]>("/admin/tasks");
    return data;
  },

  async deleteTask(userId: string, taskId: string): Promise<void> {
    await api.delete(`/admin/tasks/${userId}/${taskId}`);
  }
};
