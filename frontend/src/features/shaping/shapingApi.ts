import type { Paginated } from "@/api/client";
import { apiClient, buildQuery } from "@/api/client";
import type { AttributeItem } from "@/features/users/usersApi";

export type ProfileServiceType = "pppoe" | "hotspot" | "both";

/** Mirrors backend app/schemas/shaping.py (ProfileFieldsData). */
export interface ShapingFields {
  service_type: ProfileServiceType;
  download_kbps: number | null;
  upload_kbps: number | null;
  burst_download_kbps: number | null;
  burst_upload_kbps: number | null;
  burst_threshold_download_kbps: number | null;
  burst_threshold_upload_kbps: number | null;
  burst_time_sec: number | null;
  priority: number;
  min_download_kbps: number | null;
  min_upload_kbps: number | null;
  session_timeout_sec: number | null;
  idle_timeout_sec: number | null;
  simultaneous_use: number | null;
  mikrotik_group: string | null;
  framed_pool: string | null;
  total_quota_bytes: number | null;
  address_list: string | null;
  unifi_filter_id: string | null;
}

export interface ProfileWrite extends ShapingFields {
  name: string;
  description: string | null;
  is_active: boolean;
}

export interface Profile extends ProfileWrite {
  id: number;
  rate_limit_string: string | null;
  target_count: number;
  created_at: string;
  updated_at: string;
}

export interface PreviewResponse {
  attributes: AttributeItem[];
  check_attributes: AttributeItem[];
  rate_limit_string: string | null;
}

export interface ParseResponse {
  download_kbps: number;
  upload_kbps: number;
  burst_download_kbps: number | null;
  burst_upload_kbps: number | null;
  burst_threshold_download_kbps: number | null;
  burst_threshold_upload_kbps: number | null;
  burst_time_sec: number | null;
  priority: number;
  min_download_kbps: number | null;
  min_upload_kbps: number | null;
}

export type ApplyTarget = "group" | "user";

export interface ApplyResponse {
  target: ApplyTarget;
  name: string;
  attributes: AttributeItem[];
  check_attributes: AttributeItem[];
}

export interface ProfileTarget {
  target_type: ApplyTarget;
  target_name: string;
  applied_at: string;
}

export interface EffectiveAttribute extends AttributeItem {
  /** "user" or "group:<groupname>" */
  source: string;
}

export interface EffectiveShaping {
  username: string;
  groups: string[];
  profiles: {
    profile_id: number;
    profile_name: string;
    target_type: ApplyTarget;
    target_name: string;
  }[];
  user_attributes: AttributeItem[];
  group_attributes: Record<string, AttributeItem[]>;
  effective: EffectiveAttribute[];
  warnings: string[];
}

export const shapingApi = {
  list: (params: { search?: string; page: number; page_size: number }) =>
    apiClient.get<Paginated<Profile>>(`/shaping/profiles${buildQuery(params)}`),
  get: (id: number) => apiClient.get<Profile>(`/shaping/profiles/${id}`),
  create: (payload: ProfileWrite) => apiClient.post<Profile>("/shaping/profiles", payload),
  update: (id: number, payload: ProfileWrite) =>
    apiClient.put<Profile>(`/shaping/profiles/${id}`, payload),
  remove: (id: number) => apiClient.delete<void>(`/shaping/profiles/${id}`),
  preview: (fields: ShapingFields) => apiClient.post<PreviewResponse>("/shaping/preview", fields),
  parse: (rateLimit: string) =>
    apiClient.post<ParseResponse>("/shaping/parse", { rate_limit: rateLimit }),
  apply: (id: number, target: ApplyTarget, name: string) =>
    apiClient.post<ApplyResponse>(`/shaping/profiles/${id}/apply`, { target, name }),
  reapply: (id: number) =>
    apiClient.post<{ applied: ProfileTarget[] }>(`/shaping/profiles/${id}/reapply`),
  targets: (id: number) => apiClient.get<ProfileTarget[]>(`/shaping/profiles/${id}/targets`),
  effective: (username: string) =>
    apiClient.get<EffectiveShaping>(`/shaping/users/${encodeURIComponent(username)}/effective`),
};
