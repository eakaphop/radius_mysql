import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import type { UseFormRegister } from "react-hook-form";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import { ApiError } from "@/api/client";
import { Alert, Button, Card, Dialog, Field, Input, Select } from "@/components/ui/primitives";
import type {
  ParseResponse,
  PreviewResponse,
  Profile,
  ProfileWrite,
  ShapingFields,
} from "@/features/shaping/shapingApi";
import { shapingApi } from "@/features/shaping/shapingApi";

const GIB = 1024 ** 3;
const MAX_SLIDER_MBPS = 1000;
const PREVIEW_DEBOUNCE_MS = 400;

const optionalPositiveInt = z.number().int().min(1).nullable();

// Field types mirror backend ShapingFields; cross-field rules (burst >= rate,
// threshold <= burst, min <= rate ...) are enforced by the backend preview,
// which is the single source of truth (CLAUDE.md 6.1).
const profileSchema = z.object({
  name: z.string().min(1).max(64),
  description: z.string().max(255),
  service_type: z.enum(["pppoe", "hotspot", "both"]),
  is_active: z.boolean(),
  download_kbps: optionalPositiveInt,
  upload_kbps: optionalPositiveInt,
  burst_enabled: z.boolean(),
  burst_download_kbps: optionalPositiveInt,
  burst_upload_kbps: optionalPositiveInt,
  burst_threshold_download_kbps: optionalPositiveInt,
  burst_threshold_upload_kbps: optionalPositiveInt,
  burst_time_sec: optionalPositiveInt,
  priority: z.number().int().min(1).max(8),
  min_download_kbps: optionalPositiveInt,
  min_upload_kbps: optionalPositiveInt,
  session_timeout_sec: optionalPositiveInt,
  idle_timeout_sec: optionalPositiveInt,
  simultaneous_use: optionalPositiveInt,
  mikrotik_group: z.string().max(64),
  framed_pool: z.string().max(64),
  quota_gb: z.number().positive().nullable(),
  address_list: z.string().regex(/^[A-Za-z0-9_-]{0,64}$/),
  unifi_filter_id: z.string().max(64),
});

type ProfileFormValues = z.infer<typeof profileSchema>;
type NumericField = {
  [K in keyof ProfileFormValues]: ProfileFormValues[K] extends number | null ? K : never;
}[keyof ProfileFormValues];

const EMPTY_VALUES: ProfileFormValues = {
  name: "",
  description: "",
  service_type: "both",
  is_active: true,
  download_kbps: null,
  upload_kbps: null,
  burst_enabled: false,
  burst_download_kbps: null,
  burst_upload_kbps: null,
  burst_threshold_download_kbps: null,
  burst_threshold_upload_kbps: null,
  burst_time_sec: null,
  priority: 8,
  min_download_kbps: null,
  min_upload_kbps: null,
  session_timeout_sec: null,
  idle_timeout_sec: null,
  simultaneous_use: null,
  mikrotik_group: "",
  framed_pool: "",
  quota_gb: null,
  address_list: "",
  unifi_filter_id: "",
};

const toNullableNumber = (value: unknown): number | null =>
  value === "" || value === null || value === undefined ? null : Number(value);

function fromProfile(profile: Profile): ProfileFormValues {
  return {
    name: profile.name,
    description: profile.description ?? "",
    service_type: profile.service_type,
    is_active: profile.is_active,
    download_kbps: profile.download_kbps,
    upload_kbps: profile.upload_kbps,
    burst_enabled: profile.burst_download_kbps !== null,
    burst_download_kbps: profile.burst_download_kbps,
    burst_upload_kbps: profile.burst_upload_kbps,
    burst_threshold_download_kbps: profile.burst_threshold_download_kbps,
    burst_threshold_upload_kbps: profile.burst_threshold_upload_kbps,
    burst_time_sec: profile.burst_time_sec,
    priority: profile.priority,
    min_download_kbps: profile.min_download_kbps,
    min_upload_kbps: profile.min_upload_kbps,
    session_timeout_sec: profile.session_timeout_sec,
    idle_timeout_sec: profile.idle_timeout_sec,
    simultaneous_use: profile.simultaneous_use,
    mikrotik_group: profile.mikrotik_group ?? "",
    framed_pool: profile.framed_pool ?? "",
    quota_gb: profile.total_quota_bytes === null ? null : profile.total_quota_bytes / GIB,
    address_list: profile.address_list ?? "",
    unifi_filter_id: profile.unifi_filter_id ?? "",
  };
}

function toShapingFields(values: ProfileFormValues): ShapingFields {
  const burst = values.burst_enabled;
  return {
    service_type: values.service_type,
    download_kbps: values.download_kbps,
    upload_kbps: values.upload_kbps,
    burst_download_kbps: burst ? values.burst_download_kbps : null,
    burst_upload_kbps: burst ? values.burst_upload_kbps : null,
    burst_threshold_download_kbps: burst ? values.burst_threshold_download_kbps : null,
    burst_threshold_upload_kbps: burst ? values.burst_threshold_upload_kbps : null,
    burst_time_sec: burst ? values.burst_time_sec : null,
    priority: values.priority,
    min_download_kbps: values.min_download_kbps,
    min_upload_kbps: values.min_upload_kbps,
    session_timeout_sec: values.session_timeout_sec,
    idle_timeout_sec: values.idle_timeout_sec,
    simultaneous_use: values.simultaneous_use,
    mikrotik_group: values.mikrotik_group || null,
    framed_pool: values.service_type === "hotspot" ? null : values.framed_pool || null,
    total_quota_bytes: values.quota_gb ? Math.round(values.quota_gb * GIB) : null,
    address_list: values.address_list || null,
    unifi_filter_id: values.unifi_filter_id || null,
  };
}

function NumberInput({
  id,
  field,
  register,
  placeholder,
}: {
  id: string;
  field: NumericField;
  register: UseFormRegister<ProfileFormValues>;
  placeholder?: string;
}) {
  return (
    <Input
      id={id}
      type="number"
      min={1}
      step="any"
      placeholder={placeholder}
      {...register(field, { setValueAs: toNullableNumber })}
    />
  );
}

interface ProfileFormDialogProps {
  open: boolean;
  profile: Profile | null;
  onClose: () => void;
}

export function ProfileFormDialog({ open, profile, onClose }: ProfileFormDialogProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [importValue, setImportValue] = useState("");
  const previewRequest = useRef(0);

  const { register, handleSubmit, reset, watch, setValue, formState } =
    useForm<ProfileFormValues>({
      resolver: zodResolver(profileSchema),
      defaultValues: EMPTY_VALUES,
    });

  useEffect(() => {
    if (!open) {
      return;
    }
    reset(profile ? fromProfile(profile) : EMPTY_VALUES);
    setError(null);
    setPreview(null);
    setPreviewError(null);
    setImportValue("");
  }, [open, profile, reset]);

  const values = watch();
  const fieldsKey = JSON.stringify(toShapingFields(values));

  // Live preview: the backend builds the attributes, never the browser.
  useEffect(() => {
    if (!open) {
      return;
    }
    const requestId = ++previewRequest.current;
    const timer = window.setTimeout(() => {
      shapingApi
        .preview(JSON.parse(fieldsKey) as ShapingFields)
        .then((result) => {
          if (requestId === previewRequest.current) {
            setPreview(result);
            setPreviewError(null);
          }
        })
        .catch((err: unknown) => {
          if (requestId === previewRequest.current) {
            setPreview(null);
            setPreviewError(err instanceof ApiError ? err.message : t("common.unknownError"));
          }
        });
    }, PREVIEW_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [fieldsKey, open, t]);

  const setRateFromSlider = (field: "download_kbps" | "upload_kbps", mbps: number) => {
    setValue(field, mbps === 0 ? null : mbps * 1000, { shouldDirty: true, shouldValidate: true });
  };

  const importRateLimit = async () => {
    setError(null);
    try {
      const parsed = await shapingApi.parse(importValue);
      (Object.keys(parsed) as (keyof ParseResponse)[]).forEach((key) => {
        setValue(key, parsed[key] as never, { shouldDirty: true });
      });
      setValue("burst_enabled", parsed.burst_download_kbps !== null, { shouldDirty: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("common.unknownError"));
    }
  };

  const onSubmit = async (formValues: ProfileFormValues) => {
    setError(null);
    const payload: ProfileWrite = {
      ...toShapingFields(formValues),
      name: formValues.name,
      description: formValues.description || null,
      is_active: formValues.is_active,
    };
    try {
      if (profile) {
        const saved = await shapingApi.update(profile.id, payload);
        // CLAUDE.md 6.1: ask before re-applying, never do it automatically.
        if (
          saved.target_count > 0 &&
          window.confirm(t("profiles.confirmReapply", { count: saved.target_count }))
        ) {
          await shapingApi.reapply(saved.id);
        }
      } else {
        await shapingApi.create(payload);
      }
      await queryClient.invalidateQueries({ queryKey: ["shaping"] });
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("common.unknownError"));
    }
  };

  const errors = formState.errors;
  const invalid = (hasError: unknown) => (hasError ? t("common.invalid") : undefined);

  return (
    <Dialog
      open={open}
      size="lg"
      title={profile ? t("profiles.form.editTitle") : t("profiles.form.createTitle")}
      onClose={onClose}
    >
      <form onSubmit={handleSubmit(onSubmit)} className="grid gap-6 lg:grid-cols-[1fr_22rem]">
        <div className="space-y-5">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label={t("profiles.fields.name")} htmlFor="name" error={invalid(errors.name)}>
              <Input id="name" {...register("name")} />
            </Field>
            <Field label={t("profiles.fields.serviceType")} htmlFor="service_type">
              <Select id="service_type" className="w-full" {...register("service_type")}>
                <option value="both">{t("serviceType.both")}</option>
                <option value="pppoe">{t("serviceType.pppoe")}</option>
                <option value="hotspot">{t("serviceType.hotspot")}</option>
              </Select>
            </Field>
            <div className="sm:col-span-2">
              <Field
                label={t("profiles.fields.description")}
                htmlFor="description"
                error={invalid(errors.description)}
              >
                <Input id="description" {...register("description")} />
              </Field>
            </div>
          </div>

          <Card title={t("profiles.sections.import")}>
            <div className="flex gap-2">
              <Input
                aria-label={t("profiles.sections.import")}
                placeholder="10M/20M 20M/40M 8M/16M 10/10 5"
                value={importValue}
                onChange={(event) => setImportValue(event.target.value)}
              />
              <Button
                variant="secondary"
                disabled={!importValue.trim()}
                onClick={() => void importRateLimit()}
              >
                {t("profiles.import")}
              </Button>
            </div>
          </Card>

          <Card title={t("profiles.sections.rate")}>
            <p className="mb-3 text-xs text-foreground/60">{t("profiles.hints.unlimited")}</p>
            <div className="grid gap-4 sm:grid-cols-2">
              {(["download_kbps", "upload_kbps"] as const).map((field) => (
                <Field
                  key={field}
                  label={t(`profiles.fields.${field}`)}
                  htmlFor={field}
                  error={invalid(errors[field])}
                >
                  <input
                    type="range"
                    min={0}
                    max={MAX_SLIDER_MBPS}
                    step={1}
                    aria-label={t(`profiles.fields.${field}`)}
                    className="w-full"
                    value={Math.min(MAX_SLIDER_MBPS, Math.round((values[field] ?? 0) / 1000))}
                    onChange={(event) => setRateFromSlider(field, Number(event.target.value))}
                  />
                  <NumberInput id={field} field={field} register={register} placeholder="kbps" />
                </Field>
              ))}
              <Field label={t("profiles.fields.priority")} htmlFor="priority">
                <Select
                  id="priority"
                  className="w-full"
                  {...register("priority", { valueAsNumber: true })}
                >
                  {[1, 2, 3, 4, 5, 6, 7, 8].map((priority) => (
                    <option key={priority} value={priority}>
                      {priority}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>
          </Card>

          <Card title={t("profiles.sections.burst")}>
            <label className="mb-3 flex items-center gap-2 text-sm">
              <input type="checkbox" {...register("burst_enabled")} />
              {t("profiles.fields.burstEnabled")}
            </label>
            {values.burst_enabled && (
              <div className="grid gap-3 sm:grid-cols-2">
                {(
                  [
                    "burst_download_kbps",
                    "burst_upload_kbps",
                    "burst_threshold_download_kbps",
                    "burst_threshold_upload_kbps",
                    "burst_time_sec",
                  ] as const
                ).map((field) => (
                  <Field
                    key={field}
                    label={t(`profiles.fields.${field}`)}
                    htmlFor={field}
                    error={invalid(errors[field])}
                  >
                    <NumberInput id={field} field={field} register={register} />
                  </Field>
                ))}
              </div>
            )}
          </Card>

          <Card title={t("profiles.sections.limits")}>
            <div className="grid gap-3 sm:grid-cols-2">
              {(
                [
                  "min_download_kbps",
                  "min_upload_kbps",
                  "session_timeout_sec",
                  "idle_timeout_sec",
                  "simultaneous_use",
                  "quota_gb",
                ] as const
              ).map((field) => (
                <Field
                  key={field}
                  label={t(`profiles.fields.${field}`)}
                  htmlFor={field}
                  hint={field === "idle_timeout_sec" ? t("profiles.hints.idleTimeout") : undefined}
                  error={invalid(errors[field])}
                >
                  <NumberInput id={field} field={field} register={register} />
                </Field>
              ))}
              <Field
                label={t("profiles.fields.address_list")}
                htmlFor="address_list"
                error={invalid(errors.address_list)}
              >
                <Input id="address_list" {...register("address_list")} />
              </Field>
              <Field
                label={t("profiles.fields.mikrotik_group")}
                htmlFor="mikrotik_group"
                error={invalid(errors.mikrotik_group)}
              >
                <Input id="mikrotik_group" {...register("mikrotik_group")} />
              </Field>
              {values.service_type !== "hotspot" && (
                <Field
                  label={t("profiles.fields.framed_pool")}
                  htmlFor="framed_pool"
                  hint={t("profiles.hints.framedPool")}
                  error={invalid(errors.framed_pool)}
                >
                  <Input id="framed_pool" {...register("framed_pool")} />
                </Field>
              )}
            </div>
            <label className="mt-3 flex items-center gap-2 text-sm">
              <input type="checkbox" {...register("is_active")} />
              {t("profiles.fields.is_active")}
            </label>
          </Card>

          <Card title={t("profiles.sections.unifi")}>
            <Field
              label={t("profiles.fields.unifi_filter_id")}
              htmlFor="unifi_filter_id"
              hint={t("profiles.hints.unifiFilterId")}
              error={invalid(errors.unifi_filter_id)}
            >
              <Input id="unifi_filter_id" {...register("unifi_filter_id")} />
            </Field>
          </Card>

          {error && <Alert tone="red">{error}</Alert>}

          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={onClose}>
              {t("common.cancel")}
            </Button>
            <Button type="submit" disabled={formState.isSubmitting || previewError !== null}>
              {t("common.save")}
            </Button>
          </div>
        </div>

        <aside className="space-y-3 lg:sticky lg:top-0 lg:self-start">
          <Card title={t("profiles.preview.title")}>
            {previewError ? (
              <p className="text-sm text-red-600">{previewError}</p>
            ) : (
              <>
                <p className="text-xs text-foreground/60">Mikrotik-Rate-Limit</p>
                <p className="mb-3 break-all font-mono text-sm">
                  {preview?.rate_limit_string ?? t("profiles.preview.noRateLimit")}
                </p>
                <p className="mb-1 text-xs text-foreground/60">{t("profiles.preview.reply")}</p>
                <ul className="mb-3 space-y-1 font-mono text-xs">
                  {preview?.attributes.map((item) => (
                    <li key={item.attribute} className="break-all">
                      {item.attribute} {item.op} {item.value}
                    </li>
                  ))}
                </ul>
                {preview && preview.check_attributes.length > 0 && (
                  <>
                    <p className="mb-1 text-xs text-foreground/60">
                      {t("profiles.preview.check")}
                    </p>
                    <ul className="space-y-1 font-mono text-xs">
                      {preview.check_attributes.map((item) => (
                        <li key={item.attribute}>
                          {item.attribute} {item.op} {item.value}
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </>
            )}
            <p className="mt-3 text-xs text-foreground/60">{t("profiles.preview.groupOperator")}</p>
          </Card>
        </aside>
      </form>
    </Dialog>
  );
}
