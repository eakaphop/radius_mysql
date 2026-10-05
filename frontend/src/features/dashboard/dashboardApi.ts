import { apiClient, buildQuery } from "@/api/client";

export interface DashboardSummary {
  total_users: number;
  online_users: number;
  online_sessions: number;
  auth_accept_24h: number;
  auth_reject_24h: number;
  traffic_today_download_bytes: number;
  traffic_today_upload_bytes: number;
}

export interface TrafficPoint {
  date: string;
  download_bytes: number;
  upload_bytes: number;
}

export interface AuthStatPoint {
  hour: string;
  accept: number;
  reject: number;
}

export const dashboardApi = {
  summary: () => apiClient.get<DashboardSummary>("/dashboard/summary"),
  traffic: (days: number) =>
    apiClient.get<TrafficPoint[]>(`/dashboard/traffic${buildQuery({ days })}`),
  authStats: (hours: number) =>
    apiClient.get<AuthStatPoint[]>(`/dashboard/auth-stats${buildQuery({ hours })}`),
};
