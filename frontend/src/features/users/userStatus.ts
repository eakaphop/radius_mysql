import type { UserStatus } from "@/features/users/usersApi";

export const STATUS_TONES: Record<UserStatus, string> = {
  active: "green",
  disabled: "red",
  expired: "amber",
};
