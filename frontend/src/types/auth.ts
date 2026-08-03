// Auth-related TypeScript types mirroring the backend schemas

export type User = {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export type AuthResponse = TokenPair & {
  user: User;
};

export type LoginRequest = {
  email: string;
  password: string;
};

export type RegisterRequest = {
  email: string;
  password: string;
  full_name?: string;
};

export type LogoutResponse = {
  message: string;
};

export type ApiError = {
  detail: string | Array<{ loc: string[]; msg: string; type: string }>;
};
