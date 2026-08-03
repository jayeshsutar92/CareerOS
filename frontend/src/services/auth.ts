import { api } from "@/services/api";
import type {
  AuthResponse,
  LoginRequest,
  LogoutResponse,
  RegisterRequest,
  User,
} from "@/types/auth";

export const authService = {
  async login(payload: LoginRequest): Promise<AuthResponse> {
    const { data } = await api.post<AuthResponse>("/auth/login", payload);
    return data;
  },

  async register(payload: RegisterRequest): Promise<AuthResponse> {
    const { data } = await api.post<AuthResponse>("/auth/register", payload);
    return data;
  },

  async logout(): Promise<LogoutResponse> {
    const { data } = await api.post<LogoutResponse>("/auth/logout");
    return data;
  },

  async getMe(): Promise<User> {
    const { data } = await api.get<User>("/auth/me");
    return data;
  },

  async refreshToken(refreshToken: string) {
    const { data } = await api.post("/auth/refresh", {
      refresh_token: refreshToken,
    });
    return data;
  },
};
