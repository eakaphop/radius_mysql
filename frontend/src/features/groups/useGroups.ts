import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { GroupPayload } from "@/features/groups/groupsApi";
import { groupsApi } from "@/features/groups/groupsApi";

const GROUPS_KEY = "groups";

export function useGroupsList(params: { search?: string; page: number; page_size: number }) {
  return useQuery({
    queryKey: [GROUPS_KEY, params],
    queryFn: () => groupsApi.list(params),
  });
}

export function useGroupMutations() {
  const queryClient = useQueryClient();
  const invalidate = () => queryClient.invalidateQueries({ queryKey: [GROUPS_KEY] });

  const create = useMutation({
    mutationFn: (payload: GroupPayload & { groupname: string }) => groupsApi.create(payload),
    onSuccess: invalidate,
  });

  const update = useMutation({
    mutationFn: ({ groupname, payload }: { groupname: string; payload: GroupPayload }) =>
      groupsApi.update(groupname, payload),
    onSuccess: invalidate,
  });

  const remove = useMutation({
    mutationFn: (groupname: string) => groupsApi.remove(groupname),
    onSuccess: invalidate,
  });

  return { create, update, remove };
}
