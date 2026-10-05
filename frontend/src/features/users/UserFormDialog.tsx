import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import { ApiError } from "@/api/client";
import type { AttributeRow } from "@/components/AttributeEditor";
import { AttributeEditor } from "@/components/AttributeEditor";
import { Alert, Button, Dialog, Field, Input } from "@/components/ui/primitives";
import { useUserMutations } from "@/features/users/useUsers";
import type { UserDetail } from "@/features/users/usersApi";
import { fromLocalInputValue, toLocalInputValue } from "@/lib/format";

const userFormSchema = z.object({
  username: z.string().min(1).max(64),
  password: z.string().max(253),
  groups: z.string(),
  expiration: z.string(),
});

type UserFormValues = z.infer<typeof userFormSchema>;

interface UserFormDialogProps {
  open: boolean;
  user: UserDetail | null;
  onClose: () => void;
}

function parseGroups(value: string): string[] {
  return value
    .split(",")
    .map((group) => group.trim())
    .filter(Boolean);
}

export function UserFormDialog({ open, user, onClose }: UserFormDialogProps) {
  const { t } = useTranslation();
  const { create, update } = useUserMutations();
  const isEdit = user !== null;
  const [replyAttributes, setReplyAttributes] = useState<AttributeRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  const { register, handleSubmit, reset, formState } = useForm<UserFormValues>({
    resolver: zodResolver(
      isEdit ? userFormSchema : userFormSchema.extend({ password: z.string().min(1).max(253) })
    ),
    defaultValues: { username: "", password: "", groups: "", expiration: "" },
  });

  useEffect(() => {
    if (!open) {
      return;
    }
    setError(null);
    setReplyAttributes(user?.reply_attributes ?? []);
    reset({
      username: user?.username ?? "",
      password: "",
      groups: user?.groups.join(", ") ?? "",
      expiration: toLocalInputValue(user?.expiration ?? null),
    });
  }, [open, user, reset]);

  const onSubmit = async (values: UserFormValues) => {
    setError(null);
    const expiration = fromLocalInputValue(values.expiration) ?? null;
    try {
      if (isEdit) {
        await update.mutateAsync({
          username: user.username,
          payload: {
            groups: parseGroups(values.groups),
            expiration,
            reply_attributes: replyAttributes,
          },
        });
      } else {
        await create.mutateAsync({
          username: values.username,
          password: values.password,
          groups: parseGroups(values.groups),
          expiration,
          reply_attributes: replyAttributes,
        });
      }
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("common.unknownError"));
    }
  };

  const errors = formState.errors;

  return (
    <Dialog
      open={open}
      title={isEdit ? t("users.form.editTitle") : t("users.form.createTitle")}
      onClose={onClose}
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Field
          label={t("users.fields.username")}
          htmlFor="username"
          error={errors.username ? t("common.required") : undefined}
        >
          <Input id="username" disabled={isEdit} {...register("username")} />
        </Field>

        {!isEdit && (
          <Field
            label={t("users.fields.password")}
            htmlFor="password"
            error={errors.password ? t("common.required") : undefined}
          >
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
              {...register("password")}
            />
          </Field>
        )}

        <Field
          label={t("users.fields.groups")}
          htmlFor="groups"
          hint={t("users.fields.groupsHint")}
        >
          <Input id="groups" placeholder="pppoe-standard, staff" {...register("groups")} />
        </Field>

        <Field label={t("users.fields.expiration")} htmlFor="expiration">
          <Input id="expiration" type="datetime-local" {...register("expiration")} />
        </Field>

        <AttributeEditor
          label={t("users.fields.replyAttributes")}
          rows={replyAttributes}
          onChange={setReplyAttributes}
        />

        {error && <Alert tone="red">{error}</Alert>}

        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button type="submit" disabled={formState.isSubmitting}>
            {t("common.save")}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
