import type { Paginated } from "@/api/client";
import { apiClient, buildQuery } from "@/api/client";

export interface AuditItem {
  id: number;
  admin_id: number;
  admin_username: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  before_json: Record<string, unknown> | null;
  after_json: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string;
}

export interface AuditFilters {
  admin?: string;
  resource_type?: string;
  from?: string;
  to?: string;
}

export const auditApi = {
  list: (filters: AuditFilters, page: number, pageSize: number) =>
    apiClient.get<Paginated<AuditItem>>(
      `/audit${buildQuery({ ...filters, page, page_size: pageSize })}`
    ),
};
