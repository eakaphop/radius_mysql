import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import { ApiError } from "@/api/client";
import { Alert, Button, Dialog, Field, Input, Select } from "@/components/ui/primitives";
import type { DynAuthResult, OnlineSession } from "@/features/sessions/sessionsApi";
import { sessionsApi } from "@/features/sessions/sessionsApi";
import { shapingApi } from "@/features/shaping/shapingApi";

// Mirrors backend CoaRequest: exactly one of profile_id / rate_limit.
const coaSchema = z
  .object({
    mode: z.enum(["profile", "rate"]),
    profile_id: z.string(),
    rate_limit: z.string().max(253),
  })
  .superRefine((values, ctx) => {
    if (values.mode === "profile" && !values.profile_id) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, path: ["profile_id"], message: "required" });
    }
    if (values.mode === "rate" && !values.rate_limit.trim()) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, path: ["rate_limit"], message: "required" });
    }
  });

type CoaFormValues = z.infer<typeof coaSchema>;

interface CoaDialogProps {
  session: OnlineSession | null;
  onClose: () => void;
  onResult: (result: DynAuthResult) => void;
}

export function CoaDialog({ session, onClose, onResult }: CoaDialogProps) {
  const { t } = useTranslation();
  const [error, setError] = useState<string | null>(null);
  const { register, handleSubmit, reset, watch, formState } = useForm<CoaFormValues>({
    resolver: zodResolver(coaSchema),
    defaultValues: { mode: "profile", profile_id: "", rate_limit: "" },
  });

  const profiles = useQuery({
    queryKey: ["shaping", "profiles", "all-for-coa"],
    queryFn: () => shapingApi.list({ page: 1, page_size: 200 }),
    enabled: session !== null,
  });

  useEffect(() => {
    reset({ mode: "profile", profile_id: "", rate_limit: "" });
    setError(null);
  }, [session, reset]);

  const mode = watch("mode");

  const onSubmit = async (values: CoaFormValues) => {
    if (!session) {
      return;
    }
    setError(null);
    try {
      const result = await sessionsApi.coa(
        session.radacctid,
        values.mode === "profile"
          ? { profile_id: Number(values.profile_id) }
          : { rate_limit: values.rate_limit.trim() }
      );
      onResult(result);
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("common.unknownError"));
    }
  };

  return (
    <Dialog
      open={session !== null}
      title={t("sessions.coa.title", { username: session?.username ?? "" })}
      onClose={onClose}
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Field label={t("sessions.coa.mode")} htmlFor="coa-mode">
          <Select id="coa-mode" className="w-full" {...register("mode")}>
            <option value="profile">{t("sessions.coa.fromProfile")}</option>
            <option value="rate">{t("sessions.coa.customRate")}</option>
          </Select>
        </Field>

        {mode === "profile" ? (
          <Field
            label={t("sessions.coa.profile")}
            htmlFor="coa-profile"
            error={formState.errors.profile_id ? t("common.required") : undefined}
          >
            <Select id="coa-profile" className="w-full" {...register("profile_id")}>
              <option value="">—</option>
              {profiles.data?.items
                .filter((profile) => profile.rate_limit_string !== null)
                .map((profile) => (
                  <option key={profile.id} value={profile.id}>
                    {profile.name} ({profile.rate_limit_string})
                  </option>
                ))}
            </Select>
          </Field>
        ) : (
          <Field
            label="Mikrotik-Rate-Limit"
            htmlFor="coa-rate"
            hint={t("sessions.coa.rateHint")}
            error={formState.errors.rate_limit ? t("common.required") : undefined}
          >
            <Input id="coa-rate" placeholder="5M/20M" {...register("rate_limit")} />
          </Field>
        )}

        {error && <Alert tone="red">{error}</Alert>}

        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button type="submit" disabled={formState.isSubmitting}>
            {t("sessions.coa.submit")}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
