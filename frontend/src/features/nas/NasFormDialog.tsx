import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import { ApiError } from "@/api/client";
import { Button, Dialog, Field, Input } from "@/components/ui/primitives";
import type { Nas } from "@/features/nas/nasApi";
import { nasApi } from "@/features/nas/nasApi";

const hasControlCharacter = (value: string): boolean =>
  Array.from(value).some((char) => {
    const code = char.charCodeAt(0);
    return code < 0x20 || code === 0x7f;
  });

// Mirrors backend app/schemas/nas.py (NasWrite).
const nasSchema = z.object({
  nasname: z.string().min(1).max(128),
  shortname: z.string().max(32),
  type: z.string().regex(/^[A-Za-z0-9_-]{1,30}$/),
  secret: z
    .string()
    .min(1)
    .max(60)
    .refine((value) => !hasControlCharacter(value), { message: "control characters" }),
  description: z.string().max(200),
});

type NasFormValues = z.infer<typeof nasSchema>;

interface NasFormDialogProps {
  open: boolean;
  /** For edit, the NAS with its secret revealed. */
  nas: Nas | null;
  onClose: () => void;
  onSaved: () => void;
}

export function NasFormDialog({ open, nas, onClose, onSaved }: NasFormDialogProps) {
  const { t } = useTranslation();
  const [error, setError] = useState<string | null>(null);
  const { register, handleSubmit, reset, formState } = useForm<NasFormValues>({
    resolver: zodResolver(nasSchema),
  });

  useEffect(() => {
    if (!open) {
      return;
    }
    setError(null);
    reset({
      nasname: nas?.nasname ?? "",
      shortname: nas?.shortname ?? "",
      type: nas?.type ?? "other",
      secret: nas?.secret ?? "",
      description: nas?.description ?? "",
    });
  }, [open, nas, reset]);

  const onSubmit = async (values: NasFormValues) => {
    setError(null);
    const payload = {
      nasname: values.nasname,
      shortname: values.shortname || null,
      type: values.type,
      secret: values.secret,
      description: values.description || null,
    };
    try {
      if (nas) {
        await nasApi.update(nas.id, payload);
      } else {
        await nasApi.create(payload);
      }
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("common.unknownError"));
    }
  };

  const errors = formState.errors;

  return (
    <Dialog
      open={open}
      title={nas ? t("nas.form.editTitle") : t("nas.form.createTitle")}
      onClose={onClose}
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Field
          label={t("nas.fields.nasname")}
          htmlFor="nasname"
          hint={t("nas.fields.nasnameHint")}
          error={errors.nasname ? t("common.invalid") : undefined}
        >
          <Input id="nasname" placeholder="192.168.88.1" {...register("nasname")} />
        </Field>
        <Field
          label={t("nas.fields.shortname")}
          htmlFor="shortname"
          error={errors.shortname ? t("common.invalid") : undefined}
        >
          <Input id="shortname" {...register("shortname")} />
        </Field>
        <Field
          label={t("nas.fields.type")}
          htmlFor="type"
          error={errors.type ? t("common.invalid") : undefined}
        >
          <Input id="type" {...register("type")} />
        </Field>
        <Field
          label={t("nas.fields.secret")}
          htmlFor="secret"
          error={errors.secret ? t("common.invalid") : undefined}
        >
          <Input id="secret" type="password" autoComplete="off" {...register("secret")} />
        </Field>
        <Field
          label={t("nas.fields.description")}
          htmlFor="description"
          error={errors.description ? t("common.invalid") : undefined}
        >
          <Input id="description" {...register("description")} />
        </Field>

        {error && <p className="text-sm text-red-600">{error}</p>}

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
