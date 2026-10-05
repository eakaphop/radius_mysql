import type { Paginated } from "@/api/client";
import { apiClient, buildQuery } from "@/api/client";

export interface Nas {
  id: number;
  nasname: string;
  shortname: string | null;
  type: string | null;
  secret: string;
  description: string | null;
}

export interface NasPayload {
  nasname: string;
  shortname: string | null;
  type: string;
  secret: string;
  description: string | null;
}

export interface NasWriteResponse extends Nas {
  warning: string;
}

export const nasApi = {
  list: (params: { search?: string; page: number; page_size: number }) =>
    apiClient.get<Paginated<Nas>>(`/nas${buildQuery(params)}`),
  get: (id: number, reveal = false) =>
    apiClient.get<Nas>(`/nas/${id}${buildQuery({ reveal: reveal || undefined })}`),
  create: (payload: NasPayload) => apiClient.post<NasWriteResponse>("/nas", payload),
  update: (id: number, payload: NasPayload) =>
    apiClient.put<NasWriteResponse>(`/nas/${id}`, payload),
  remove: (id: number) => apiClient.delete<{ warning: string }>(`/nas/${id}`),
};
