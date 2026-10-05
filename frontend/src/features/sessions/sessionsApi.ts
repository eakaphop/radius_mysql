import type { Paginated } from "@/api/client";
import { apiClient, buildQuery } from "@/api/client";
import type { AccountingItem } from "@/features/accounting/accountingApi";

export type SessionService = "all" | "pppoe" | "hotspot";

export interface OnlineSession extends AccountingItem {
  service_type: "pppoe" | "hotspot" | "unknown";
  acctupdatetime: string | null;
}

export interface SessionCapabilities {
  pod_enabled: boolean;
  coa_enabled: boolean;
}

export interface DynAuthResult {
  success: boolean;
  response: string | null;
  error_cause: string | null;
  detail: string;
}

export type CoaPayload = { profile_id: number } | { rate_limit: string };

export const sessionsApi = {
  capabilities: () => apiClient.get<SessionCapabilities>("/sessions/capabilities"),
  online: (service: SessionService, page: number, pageSize: number) =>
    apiClient.get<Paginated<OnlineSession>>(
      `/sessions/online${buildQuery({ service, page, page_size: pageSize })}`
    ),
  disconnect: (radacctid: number) =>
    apiClient.post<DynAuthResult>(`/sessions/${radacctid}/disconnect`),
  coa: (radacctid: number, payload: CoaPayload) =>
    apiClient.post<DynAuthResult>(`/sessions/${radacctid}/coa`, payload),
};
