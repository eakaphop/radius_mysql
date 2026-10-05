import type { Paginated } from "@/api/client";
import { apiClient, buildQuery } from "@/api/client";
import type { AccountingItem } from "@/features/accounting/accountingApi";

export type UserStatus = "active" | "disabled" | "expired";
export type ServiceType = "pppoe" | "hotspot" | "unknown";

export interface AttributeItem {
  attribute: string;
  op: string;
  value: string;
}

export interface UserListItem {
  username: string;
  status: UserStatus;
  has_password: boolean;
  groups: string[];
  service_type: ServiceType;
  expiration: string | null;
}

export interface UserDetail extends UserListItem {
  check_attributes: AttributeItem[];
  reply_attributes: AttributeItem[];
}

export interface UserListParams {
  search?: string;
  group?: string;
  status?: UserStatus | "";
  page: number;
  page_size: number;
}

export interface UserCreatePayload {
  username: string;
  password: string;
  groups: string[];
  expiration: string | null;
  reply_attributes: AttributeItem[];
}

export interface UserUpdatePayload {
  groups: string[];
  expiration: string | null;
  reply_attributes: AttributeItem[];
}

const userPath = (username: string) => `/users/${encodeURIComponent(username)}`;

export const usersApi = {
  list: (params: UserListParams) =>
    apiClient.get<Paginated<UserListItem>>(`/users${buildQuery({ ...params })}`),
  get: (username: string) => apiClient.get<UserDetail>(userPath(username)),
  create: (payload: UserCreatePayload) => apiClient.post<UserDetail>("/users", payload),
  update: (username: string, payload: UserUpdatePayload) =>
    apiClient.put<UserDetail>(userPath(username), payload),
  setPassword: (username: string, password: string) =>
    apiClient.patch<void>(`${userPath(username)}/password`, { password }),
  setStatus: (username: string, enabled: boolean) =>
    apiClient.patch<UserDetail>(`${userPath(username)}/status`, { enabled }),
  remove: (username: string) => apiClient.delete<void>(userPath(username)),
  sessions: (username: string, page: number, pageSize: number) =>
    apiClient.get<Paginated<AccountingItem>>(
      `${userPath(username)}/sessions${buildQuery({ page, page_size: pageSize })}`
    ),
};
