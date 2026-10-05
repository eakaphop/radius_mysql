import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import { ApiError } from "@/api/client";
import { Alert, Button, Card, Dialog, Field, Input, Select } from "@/components/ui/primitives";
import type { ApplyResponse, Profile } from "@/features/shaping/shapingApi";
import { shapingApi } from "@/features/shaping/shapingApi";
import { formatDateTime } from "@/lib/format";

// Mirrors backend ApplyRequest.
const applySchema = z.object({
  target: z.enum(["group", "user"]),
  name: z.string().min(1).max(64),
});
type ApplyFormValues = z.infer<typeof applySchema>;

interface ApplyProfileDialogProps {
  profile: Profile | null;
  onClose: () => void;
}

export function ApplyProfileDialog({ profile, onClose }: ApplyProfileDialogProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [result, setResult] = useState<ApplyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { register, handleSubmit, reset, formState } = useForm<ApplyFormValues>({
    resolver: zodResolver(applySchema),
    defaultValues: { target: "group", name: "" },
  });

  const targets = useQuery({
    queryKey: ["shaping", "targets", profile?.id],
    queryFn: () => shapingApi.targets((profile as Profile).id),
    enabled: profile !== null,
  });

  useEffect(() => {
    reset({ target: "group", name: profile?.name ?? "" });
    setResult(null);
    setError(null);
  }, [profile, reset]);

  const onSubmit = async (values: ApplyFormValues) => {
    if (!profile) {
      return;
    }
    setError(null);
    setResult(null);
    try {
      setResult(await shapingApi.apply(profile.id, values.target, values.name));
      await queryClient.invalidateQueries({ queryKey: ["shaping"] });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("common.unknownError"));
    }
  };

  return (
    <Dialog
      open={profile !== null}
      title={t("profiles.apply.title", { name: profile?.name ?? "" })}
      onClose={onClose}
    >
      <div className="space-y-4">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-[10rem_1fr]">
            <Field label={t("profiles.apply.target")} htmlFor="apply-target">
              <Select id="apply-target" className="w-full" {...register("target")}>
                <option value="group">{t("profiles.apply.targets.group")}</option>
                <option value="user">{t("profiles.apply.targets.user")}</option>
              </Select>
            </Field>
            <Field
              label={t("profiles.apply.name")}
              htmlFor="apply-name"
              hint={t("profiles.apply.nameHint")}
              error={formState.errors.name ? t("common.required") : undefined}
            >
              <Input id="apply-name" {...register("name")} />
            </Field>
          </div>
          <p className="text-xs text-foreground/60">{t("profiles.apply.replaceNotice")}</p>
          {error && <Alert tone="red">{error}</Alert>}
          {result && (
            <Alert tone="green">
              <p>{t("profiles.apply.success", { name: result.name })}</p>
              <ul className="mt-1 font-mono text-xs">
                {[...result.attributes, ...result.check_attributes].map((item) => (
                  <li key={`${item.attribute}-${item.value}`}>
                    {item.attribute} {item.op} {item.value}
                  </li>
                ))}
              </ul>
            </Alert>
          )}
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={onClose}>
              {t("common.close")}
            </Button>
            <Button type="submit" disabled={formState.isSubmitting}>
              {t("profiles.apply.submit")}
            </Button>
          </div>
        </form>

        <Card title={t("profiles.apply.currentTargets")}>
          {targets.isLoading && <p className="text-sm text-foreground/60">{t("table.loading")}</p>}
          {targets.isError && <p className="text-sm text-red-600">{t("table.error")}</p>}
          {targets.data && targets.data.length === 0 && (
            <p className="text-sm text-foreground/60">{t("profiles.apply.noTargets")}</p>
          )}
          <ul className="space-y-1 text-sm">
            {targets.data?.map((target) => (
              <li key={`${target.target_type}:${target.target_name}`}>
                {t(`profiles.apply.targets.${target.target_type}`)}: {target.target_name}{" "}
                <span className="text-foreground/60">({formatDateTime(target.applied_at)})</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </Dialog>
  );
}
