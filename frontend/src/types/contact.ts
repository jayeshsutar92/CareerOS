export type ContactRoleCategory =
  | "hr"
  | "recruiter"
  | "hiring_manager"
  | "engineering_manager"
  | "other";

export type ContactMethodType = "email" | "linkedin" | "phone" | "website" | "source_page";

export interface ContactMethod {
  type: ContactMethodType;
  value: string;
}

export interface ContactRead {
  id: string;
  company_id: string | null;
  name: string;
  role: string;
  role_category: ContactRoleCategory;
  company_name: string;
  contact_methods: ContactMethod[];
  source_url: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ContactListResponse {
  items: ContactRead[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ContactDiscoveryRequest {
  company_name: string;
  company_id?: string;
  source_urls: string[];
  run_in_background?: boolean;
}

export interface ContactDiscoveryResponse {
  status: "queued" | "completed";
  task_id: string | null;
  contacts: ContactRead[];
  discovered: number;
  stored: number;
}

export type ContactSortField = "name" | "role" | "company_name" | "created_at" | "updated_at";
export type SortOrder = "asc" | "desc";

export interface ContactListParams {
  page?: number;
  page_size?: number;
  search?: string;
  company_name?: string;
  role_category?: ContactRoleCategory;
  sort_by?: ContactSortField;
  sort_order?: SortOrder;
}
