import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type {
  UserCreatePayload,
  UserListParams,
  UserUpdatePayload,
} from "@/features/users/usersApi";
import { usersApi } from "@/features/users/usersApi";

const USERS_KEY = "users";

export function useUsersList(params: UserListParams) {
  return useQuery({
    queryKey: [USERS_KEY, params],
    queryFn: () => usersApi.list(params),
  });
}

export function useUser(username: string | null) {
  return useQuery({
    queryKey: [USERS_KEY, "detail", username],
    queryFn: () => usersApi.get(username as string),
    enabled: username !== null,
  });
}

export function useUserMutations() {
  const queryClient = useQueryClient();
  const invalidate = () => queryClient.invalidateQueries({ queryKey: [USERS_KEY] });

  const create = useMutation({
    mutationFn: (payload: UserCreatePayload) => usersApi.create(payload),
    onSuccess: invalidate,
  });

  const update = useMutation({
    mutationFn: ({ username, payload }: { username: string; payload: UserUpdatePayload }) =>
      usersApi.update(username, payload),
    onSuccess: invalidate,
  });

  const setPassword = useMutation({
    mutationFn: ({ username, password }: { username: string; password: string }) =>
      usersApi.setPassword(username, password),
    onSuccess: invalidate,
  });

  const setStatus = useMutation({
    mutationFn: ({ username, enabled }: { username: string; enabled: boolean }) =>
      usersApi.setStatus(username, enabled),
    onSuccess: invalidate,
  });

  const remove = useMutation({
    mutationFn: (username: string) => usersApi.remove(username),
    onSuccess: invalidate,
  });

  return { create, update, setPassword, setStatus, remove };
}
