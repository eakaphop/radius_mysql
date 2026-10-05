import { apiClient } from "@/api/client";

export type AdminRole = "admin" | "viewer";

export interface Admin {
  id: number;
  username: string;
  role: AdminRole;
  is_active: boolean;
  last_login_at: string | null;
}

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  admin: Admin;
}

export const authApi = {
  login: (username: string, password: string) =>
    apiClient.post<TokenResponse>("/auth/login", { username, password }),
  refresh: () => apiClient.post<TokenResponse>("/auth/refresh"),
  logout: () => apiClient.post<void>("/auth/logout"),
  me: () => apiClient.get<Admin>("/auth/me"),
  changePassword: (currentPassword: string, newPassword: string) =>
    apiClient.patch<void>("/auth/me/password", {
      current_password: currentPassword,
      new_password: newPassword,
    }),
};
