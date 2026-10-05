import type { Paginated } from "@/api/client";
import { apiClient, buildQuery } from "@/api/client";
import type { AttributeItem } from "@/features/users/usersApi";

export interface GroupListItem {
  groupname: string;
  member_count: number;
}

export interface GroupDetail {
  groupname: string;
  member_count: number;
  check_attributes: AttributeItem[];
  reply_attributes: AttributeItem[];
}

export interface GroupMember {
  username: string;
  priority: number;
}

export interface GroupPayload {
  check_attributes: AttributeItem[];
  reply_attributes: AttributeItem[];
}

const groupPath = (groupname: string) => `/groups/${encodeURIComponent(groupname)}`;

export const groupsApi = {
  list: (params: { search?: string; page: number; page_size: number }) =>
    apiClient.get<Paginated<GroupListItem>>(`/groups${buildQuery({ ...params })}`),
  get: (groupname: string) => apiClient.get<GroupDetail>(groupPath(groupname)),
  create: (payload: GroupPayload & { groupname: string }) =>
    apiClient.post<GroupDetail>("/groups", payload),
  update: (groupname: string, payload: GroupPayload) =>
    apiClient.put<GroupDetail>(groupPath(groupname), payload),
  remove: (groupname: string) => apiClient.delete<void>(groupPath(groupname)),
  members: (groupname: string, params: { page: number; page_size: number }) =>
    apiClient.get<Paginated<GroupMember>>(`${groupPath(groupname)}/members${buildQuery(params)}`),
};
