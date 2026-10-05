import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";

import { ApiError } from "@/api/client";
import { useTheme } from "@/app/ThemeProvider";
import { MoonIcon, SunIcon } from "@/components/ui/icons";
import { Button, Field, Input } from "@/components/ui/primitives";
import { useAuth } from "@/features/auth/AuthProvider";

const loginSchema = z.object({
  username: z.string().min(1),
  password: z.string().min(1),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export function LoginPage() {
  const { t } = useTranslation();
  const { admin, isLoading, login } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({ resolver: zodResolver(loginSchema) });

  if (!isLoading && admin) {
    const redirectTo = (location.state as { from?: string } | null)?.from ?? "/";
    return <Navigate to={redirectTo} replace />;
  }

  const onSubmit = async (values: LoginFormValues) => {
    setError(null);
    try {
      await login(values.username, values.password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("auth.login.unknownError"));
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-muted p-4">
      <button
        type="button"
        onClick={toggleTheme}
        aria-label={theme === "dark" ? t("theme.light") : t("theme.dark")}
        title={theme === "dark" ? t("theme.light") : t("theme.dark")}
        className="absolute right-4 top-4 rounded-md p-1.5 text-foreground/70 transition-colors hover:bg-card hover:text-foreground"
      >
        {theme === "dark" ? <SunIcon /> : <MoonIcon />}
      </button>
      <form
        onSubmit={handleSubmit(onSubmit)}
        className="w-full max-w-sm space-y-5 rounded-xl border border-border bg-card p-8 shadow-lg"
      >
        <div className="space-y-1 text-center">
          <h1 className="text-xl font-semibold">{t("app.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("auth.login.title")}</p>
        </div>

        <Field
          label={t("auth.login.username")}
          htmlFor="username"
          error={errors.username ? t("auth.login.required") : undefined}
        >
          <Input id="username" type="text" autoComplete="username" {...register("username")} />
        </Field>

        <Field
          label={t("auth.login.password")}
          htmlFor="password"
          error={errors.password ? t("auth.login.required") : undefined}
        >
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            {...register("password")}
          />
        </Field>

        {error && <p className="text-sm text-destructive">{error}</p>}

        <Button type="submit" disabled={isSubmitting} className="w-full py-2">
          {t("auth.login.submit")}
        </Button>
      </form>
    </div>
  );
}
