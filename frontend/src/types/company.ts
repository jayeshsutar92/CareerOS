export interface CompanyIntelligenceRequest {
  website_url: string;
  company_name?: string;
  company_id?: string;
  run_in_background?: boolean;
}

export interface CompanyIntelligenceRead {
  id: string;
  company_id: string | null;
  company_name: string;
  website_url: string;
  overview: string | null;
  products_services: string[];
  tech_stack: string[];
  careers_url: string | null;
  about_url: string | null;
  contact_info: Record<string, unknown>;
  raw_content: Record<string, unknown>;
  raw_summary: string | null;
  status: string;
  error: string | null;
  analysis_version: number;
  last_analyzed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CompanyIntelligenceResponse {
  status: string;
  task_id: string | null;
  data: CompanyIntelligenceRead | null;
}

export interface CompanyIntelligenceListResponse {
  items: CompanyIntelligenceRead[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface CompanyListParams {
  page?: number;
  page_size?: number;
  search?: string;
}
