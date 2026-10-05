import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { z } from "zod";

import { ApiError } from "@/api/client";
import { DataTable } from "@/components/data-table/DataTable";
import { Pagination } from "@/components/data-table/Pagination";
import { Alert, Badge, Button, Card, Field, Input, Tabs } from "@/components/ui/primitives";
import type { AccountingItem } from "@/features/accounting/accountingApi";
import { useIsAdmin } from "@/features/auth/useIsAdmin";
import { PostAuthLog } from "@/features/postauth/PostAuthLog";
import { EffectiveShaping } from "@/features/shaping/EffectiveShaping";
import { useUser, useUserMutations } from "@/features/users/useUsers";
import type { AttributeItem } from "@/features/users/usersApi";
import { usersApi } from "@/features/users/usersApi";
import { STATUS_TONES } from "@/features/users/userStatus";
import { formatBytes, formatDateTime, formatDuration } from "@/lib/format";

const PAGE_SIZE = 25;

type TabId = "info" | "reply" | "shaping" | "sessions" | "authlog";

function AttributesTable({ rows }: { rows: AttributeItem[] }) {
  const { t } = useTranslation();
  const columns = useMemo<ColumnDef<AttributeItem, unknown>[]>(
    () => [
      { accessorKey: "attribute", header: t("attributes.attribute") },
      { accessorKey: "op", header: t("attributes.operator") },
      { accessorKey: "value", header: t("attributes.value") },
    ],
    [t]
  );
  return <DataTable columns={columns} data={rows} isLoading={false} isError={false} />;
}

function UserSessions({ username }: { username: string }) {
  const { t } = useTranslation();
  const [page, setPage] = useState(1);
  const { data, isLoading, isError } = useQuery({
    queryKey: ["users", "sessions", username, page],
    queryFn: () => usersApi.sessions(username, page, PAGE_SIZE),
  });

  const columns = useMemo<ColumnDef<AccountingItem, unknown>[]>(
    () => [
      {
        id: "start",
        header: t("accounting.fields.acctstarttime"),
        cell: ({ row }) => formatDateTime(row.original.acctstarttime),
      },
      {
        id: "stop",
        header: t("accounting.fields.acctstoptime"),
        cell: ({ row }) =>
          row.original.acctstoptime ? (
            formatDateTime(row.original.acctstoptime)
          ) : (
            <Badge tone="green">{t("sessions.online")}</Badge>
          ),
      },
      { accessorKey: "nasipaddress", header: t("accounting.fields.nasipaddress") },
      { accessorKey: "framedipaddress", header: t("accounting.fields.framedipaddress") },
      {
        id: "duration",
        header: t("accounting.fields.acctsessiontime"),
        cell: ({ row }) => formatDuration(row.original.acctsessiontime),
      },
      {
        id: "download",
        header: t("accounting.fields.download"),
        cell: ({ row }) => formatBytes(row.original.acctoutputoctets),
      },
      {
        id: "upload",
        header: t("accounting.fields.upload"),
        cell: ({ row }) => formatBytes(row.original.acctinputoctets),
      },
      { accessorKey: "acctterminatecause", header: t("accounting.fields.acctterminatecause") },
    ],
    [t]
  );

  return (
    <div className="space-y-3">
      <DataTable
        columns={columns}
        data={data?.items ?? []}
        isLoading={isLoading}
        isError={isError}
      />
      <Pagination
        page={page}
        pageSize={PAGE_SIZE}
        total={data?.total ?? 0}
        onPageChange={setPage}
      />
    </div>
  );
}

const passwordSchema = z.object({ password: z.string().min(1).max(253) });
type PasswordFormValues = z.infer<typeof passwordSchema>;

function SetPasswordForm({ username }: { username: string }) {
  const { t } = useTranslation();
  const [message, setMessage] = useState<{ tone: string; text: string } | null>(null);
  const { register, handleSubmit, reset, formState } = useForm<PasswordFormValues>({
    resolver: zodResolver(passwordSchema),
    defaultValues: { password: "" },
  });
  const mutation = useMutation({
    mutationFn: (password: string) => usersApi.setPassword(username, password),
  });

  const onSubmit = async (values: PasswordFormValues) => {
    try {
      await mutation.mutateAsync(values.password);
      reset({ password: "" });
      setMessage({ tone: "green", text: t("users.detail.passwordChanged") });
    } catch (err) {
      setMessage({
        tone: "red",
        text: err instanceof ApiError ? err.message : t("common.unknownError"),
      });
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
      <Field
        label={t("users.detail.newPassword")}
        htmlFor="new-password"
        error={formState.errors.password ? t("common.required") : undefined}
      >
        <Input
          id="new-password"
          type="password"
          autoComplete="new-password"
          {...register("password")}
        />
      </Field>
      {message && (
        <Alert tone={message.tone} onDismiss={() => setMessage(null)}>
          {message.text}
        </Alert>
      )}
      <Button type="submit" disabled={formState.isSubmitting}>
        {t("users.detail.setPassword")}
      </Button>
    </form>
  );
}

export function UserDetailPage() {
  const { t } = useTranslation();
  const { username = "" } = useParams();
  const canWrite = useIsAdmin();
  const [tab, setTab] = useState<TabId>("info");
  const { data: user, isLoading, isError } = useUser(username);
  const { setStatus } = useUserMutations();

  const tabs: { id: TabId; label: string }[] = [
    { id: "info", label: t("users.detail.tabs.info") },
    { id: "reply", label: t("users.detail.tabs.reply") },
    { id: "shaping", label: t("users.detail.tabs.shaping") },
    { id: "sessions", label: t("users.detail.tabs.sessions") },
    { id: "authlog", label: t("users.detail.tabs.authlog") },
  ];

  return (
    <div className="space-y-4 p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <Link to="/users" className="text-sm text-primary hover:underline">
            ← {t("users.title")}
          </Link>
          <h1 className="text-xl font-semibold">{username}</h1>
          {user && (
            <Badge tone={STATUS_TONES[user.status]}>{t(`users.status.${user.status}`)}</Badge>
          )}
        </div>
        {user && canWrite && (
          <Button
            variant="secondary"
            onClick={() => setStatus.mutate({ username, enabled: user.status === "disabled" })}
          >
            {user.status === "disabled" ? t("users.enable") : t("users.disable")}
          </Button>
        )}
      </div>

      {isLoading && <p className="text-foreground/60">{t("table.loading")}</p>}
      {isError && <Alert tone="red">{t("users.detail.notFound")}</Alert>}

      {user && (
        <>
          <Tabs tabs={tabs} active={tab} onChange={setTab} />

          {tab === "info" && (
            <div className="grid gap-4 lg:grid-cols-2">
              <Card title={t("users.detail.summary")}>
                <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-2 text-sm">
                  <dt className="text-foreground/60">{t("users.fields.serviceType")}</dt>
                  <dd>
                    <Badge tone="blue">{t(`serviceType.${user.service_type}`)}</Badge>
                  </dd>
                  <dt className="text-foreground/60">{t("users.fields.groups")}</dt>
                  <dd>{user.groups.join(", ") || "—"}</dd>
                  <dt className="text-foreground/60">{t("users.fields.expiration")}</dt>
                  <dd>{formatDateTime(user.expiration)}</dd>
                  <dt className="text-foreground/60">{t("users.fields.password")}</dt>
                  <dd>
                    {user.has_password
                      ? t("users.detail.hasPassword")
                      : t("users.detail.noPassword")}
                  </dd>
                </dl>
              </Card>
              {canWrite && (
                <Card title={t("users.detail.setPassword")}>
                  <SetPasswordForm username={username} />
                </Card>
              )}
              <div className="lg:col-span-2">
                <Card title={t("users.detail.checkAttributes")}>
                  <AttributesTable rows={user.check_attributes} />
                </Card>
              </div>
            </div>
          )}

          {tab === "reply" && <AttributesTable rows={user.reply_attributes} />}
          {tab === "shaping" && <EffectiveShaping username={username} />}
          {tab === "sessions" && <UserSessions username={username} />}
          {tab === "authlog" && <PostAuthLog username={username} />}
        </>
      )}
    </div>
  );
}
