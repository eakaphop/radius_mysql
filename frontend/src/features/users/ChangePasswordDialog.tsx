import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import { ApiError } from "@/api/client";
import { Alert, Button, Dialog, Field, Input } from "@/components/ui/primitives";
import { useUserMutations } from "@/features/users/useUsers";

const changePasswordSchema = z.object({ password: z.string().min(1).max(253) });
type ChangePasswordValues = z.infer<typeof changePasswordSchema>;

interface ChangePasswordDialogProps {
  username: string | null;
  onClose: () => void;
}

export function ChangePasswordDialog({ username, onClose }: ChangePasswordDialogProps) {
  const { t } = useTranslation();
  const { setPassword } = useUserMutations();
  const [error, setError] = useState<string | null>(null);
  const open = username !== null;

  const { register, handleSubmit, reset, formState } = useForm<ChangePasswordValues>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: { password: "" },
  });

  useEffect(() => {
    if (!open) {
      return;
    }
    setError(null);
    reset({ password: "" });
  }, [open, reset]);

  const onSubmit = async (values: ChangePasswordValues) => {
    if (!username) {
      return;
    }
    setError(null);
    try {
      await setPassword.mutateAsync({ username, password: values.password });
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("common.unknownError"));
    }
  };

  const errors = formState.errors;

  return (
    <Dialog open={open} title={t("users.changePassword")} onClose={onClose}>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Field
          label={t("users.detail.newPassword")}
          htmlFor="change-password-new"
          error={errors.password ? t("common.required") : undefined}
        >
          <Input
            id="change-password-new"
            type="password"
            autoComplete="new-password"
            {...register("password")}
          />
        </Field>

        {error && <Alert tone="red">{error}</Alert>}

        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button type="submit" disabled={formState.isSubmitting}>
            {t("users.detail.setPassword")}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
