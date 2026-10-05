import type { Paginated } from "@/api/client";
import { apiClient, buildQuery } from "@/api/client";

export type PostAuthReply = "Access-Accept" | "Access-Reject";

export interface PostAuthItem {
  id: number;
  username: string;
  reply: string;
  authdate: string;
}

export interface PostAuthFilters {
  username?: string;
  reply?: PostAuthReply | "";
  from?: string;
  to?: string;
}

export const postauthApi = {
  list: (filters: PostAuthFilters, page: number, pageSize: number) =>
    apiClient.get<Paginated<PostAuthItem>>(
      `/postauth${buildQuery({ ...filters, page, page_size: pageSize })}`
    ),
};
