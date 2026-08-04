export interface UserProfileContext {
  name?: string;
  current_role?: string | null;
  bio_summary?: string | null;
  skills?: string[];
}

export interface PortfolioLinkContext {
  title: string;
  url: string;
  description?: string | null;
  tech_stack?: string[];
}

export interface CompanyContext {
  company_name: string;
  website_url?: string | null;
  overview?: string | null;
  tech_stack?: string[];
  key_insights?: string[];
}

export interface RecipientContext {
  name?: string | null;
  role?: string | null;
  email?: string | null;
}

export interface EmailPersonalizationRequest {
  template_content: string;
  template_name?: string | null;
  user_profile?: UserProfileContext | null;
  portfolio_links?: PortfolioLinkContext[];
  resume_link?: string | null;
  company_intelligence?: CompanyContext | null;
  company_intelligence_id?: string | null;
  recipient?: RecipientContext | null;
  contact_id?: string | null;
  custom_instructions?: string | null;
  user_id?: string | null;
  save_draft?: boolean;
  run_in_background?: boolean;
}

export interface EmailPersonalizationRead {
  id?: string | null;
  subject: string;
  body: string;
  personalized_hooks?: string[];
  confidence_score?: number;
  is_valid?: boolean;
  validation_warnings?: string[];
  template_name?: string | null;
  status?: string;
}

export interface EmailPersonalizationResponse {
  status: string;
  task_id?: string | null;
  data?: EmailPersonalizationRead | null;
}
