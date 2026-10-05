import { useAuth } from "@/features/auth/AuthProvider";

/** Write actions are admin-only; the backend enforces it, the UI just hides them. */
export function useIsAdmin(): boolean {
  return useAuth().admin?.role === "admin";
}
