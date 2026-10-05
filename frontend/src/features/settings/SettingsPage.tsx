import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import { ApiError } from "@/api/client";
import { Alert, Button, Card, Field, Input, Select } from "@/components/ui/primitives";
import type { Language } from "@/app/i18n";
import { changeLanguage, SUPPORTED_LANGUAGES } from "@/app/i18n";
import { authApi } from "@/features/auth/authApi";
import { useAuth } from "@/features/auth/AuthProvider";

const passwordSchema = z
  .object({
    current_password: z.string().min(1),
    new_password: z.string().min(8).max(255),
    confirm_password: z.string().min(1),
  })
  .refine((values) => values.new_password === values.confirm_password, {
    path: ["confirm_password"],
    message: "mismatch",
  });

type PasswordFormValues = z.infer<typeof passwordSchema>;

export function SettingsPage() {
  const { t, i18n } = useTranslation();
  const { admin } = useAuth();
  const [message, setMessage] = useState<{ tone: string; text: string } | null>(null);

  const { register, handleSubmit, reset, formState } = useForm<PasswordFormValues>({
    resolver: zodResolver(passwordSchema),
    defaultValues: { current_password: "", new_password: "", confirm_password: "" },
  });

  const onSubmit = async (values: PasswordFormValues) => {
    setMessage(null);
    try {
      await authApi.changePassword(values.current_password, values.new_password);
      reset();
      setMessage({ tone: "green", text: t("settings.passwordChanged") });
    } catch (err) {
      setMessage({
        tone: "red",
        text: err instanceof ApiError ? err.message : t("common.unknownError"),
      });
    }
  };

  const errors = formState.errors;

  return (
    <div className="max-w-xl space-y-6 p-6">
      <h1 className="text-xl font-semibold">{t("settings.title")}</h1>

      <Card title={t("settings.account")}>
        <p className="text-sm text-foreground/70">
          {admin?.username} · {t(`auth.roles.${admin?.role}`)}
        </p>
      </Card>

      <Card title={t("settings.language")}>
        <Field label={t("settings.language")} htmlFor="language">
          <Select
            id="language"
            className="w-full max-w-xs"
            value={i18n.language}
            onChange={(event) => changeLanguage(event.target.value as Language)}
          >
            {SUPPORTED_LANGUAGES.map((lang) => (
              <option key={lang} value={lang}>
                {t(`settings.languages.${lang}`)}
              </option>
            ))}
          </Select>
        </Field>
      </Card>

      <Card title={t("settings.changePassword")}>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
          <Field
            label={t("settings.currentPassword")}
            htmlFor="current_password"
            error={errors.current_password ? t("common.required") : undefined}
          >
            <Input
              id="current_password"
              type="password"
              autoComplete="current-password"
              {...register("current_password")}
            />
          </Field>
          <Field
            label={t("settings.newPassword")}
            htmlFor="new_password"
            hint={t("settings.newPasswordHint")}
            error={errors.new_password ? t("common.required") : undefined}
          >
            <Input
              id="new_password"
              type="password"
              autoComplete="new-password"
              {...register("new_password")}
            />
          </Field>
          <Field
            label={t("settings.confirmPassword")}
            htmlFor="confirm_password"
            error={errors.confirm_password ? t("settings.passwordMismatch") : undefined}
          >
            <Input
              id="confirm_password"
              type="password"
              autoComplete="new-password"
              {...register("confirm_password")}
            />
          </Field>
          {message && (
            <Alert tone={message.tone} onDismiss={() => setMessage(null)}>
              {message.text}
            </Alert>
          )}
          <Button type="submit" disabled={formState.isSubmitting}>
            {t("settings.changePassword")}
          </Button>
        </form>
      </Card>
    </div>
  );
}
