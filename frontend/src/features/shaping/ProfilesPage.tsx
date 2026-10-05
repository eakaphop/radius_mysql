import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { useCallback, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "@/api/client";
import { DataTable } from "@/components/data-table/DataTable";
import { Pagination } from "@/components/data-table/Pagination";
import { Alert, Badge, Button, Input } from "@/components/ui/primitives";
import { useIsAdmin } from "@/features/auth/useIsAdmin";
import { ApplyProfileDialog } from "@/features/shaping/ApplyProfileDialog";
import { ProfileFormDialog } from "@/features/shaping/ProfileFormDialog";
import type { Profile } from "@/features/shaping/shapingApi";
import { shapingApi } from "@/features/shaping/shapingApi";
import { formatBytes } from "@/lib/format";

const PAGE_SIZE = 25;

export function ProfilesPage() {
  const { t } = useTranslation();
  const canWrite = useIsAdmin();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Profile | null>(null);
  const [applying, setApplying] = useState<Profile | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["shaping", "profiles", search, page],
    queryFn: () => shapingApi.list({ search, page, page_size: PAGE_SIZE }),
  });

  const remove = useCallback(
    async (profile: Profile) => {
      if (!window.confirm(t("profiles.confirmDelete", { name: profile.name }))) {
        return;
      }
      setError(null);
      try {
        await shapingApi.remove(profile.id);
        await queryClient.invalidateQueries({ queryKey: ["shaping"] });
      } catch (err) {
        setError(err instanceof ApiError ? err.message : t("common.unknownError"));
      }
    },
    [t, queryClient]
  );

  const columns = useMemo<ColumnDef<Profile, unknown>[]>(
    () => [
      { accessorKey: "name", header: t("profiles.fields.name") },
      {
        id: "service_type",
        header: t("profiles.fields.serviceType"),
        cell: ({ row }) => <Badge tone="blue">{t(`serviceType.${row.original.service_type}`)}</Badge>,
      },
      {
        id: "rate",
        header: t("profiles.fields.shaping"),
        cell: ({ row }) => (
          <div className="space-y-0.5 text-xs">
            <div>
              <span className="text-muted-foreground">Mikrotik: </span>
              <code>{row.original.rate_limit_string ?? t("profiles.preview.noRateLimit")}</code>
            </div>
            {row.original.unifi_filter_id && (
              <div>
                <span className="text-muted-foreground">UniFi: </span>
                <code>{row.original.unifi_filter_id}</code>
              </div>
            )}
          </div>
        ),
      },
      {
        id: "quota",
        header: t("profiles.fields.quota_gb"),
        cell: ({ row }) => formatBytes(row.original.total_quota_bytes),
      },
      { accessorKey: "target_count", header: t("profiles.fields.targetCount") },
      {
        id: "active",
        header: t("profiles.fields.is_active"),
        cell: ({ row }) =>
          row.original.is_active ? (
            <Badge tone="green">{t("common.yes")}</Badge>
          ) : (
            <Badge>{t("common.no")}</Badge>
          ),
      },
      {
        id: "actions",
        header: "",
        cell: ({ row }) =>
          canWrite ? (
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setApplying(row.original)}>
                {t("profiles.apply.button")}
              </Button>
              <Button
                variant="secondary"
                onClick={() => {
                  setEditing(row.original);
                  setFormOpen(true);
                }}
              >
                {t("common.edit")}
              </Button>
              <Button variant="danger" onClick={() => void remove(row.original)}>
                {t("common.delete")}
              </Button>
            </div>
          ) : null,
      },
    ],
    [t, canWrite, remove]
  );

  return (
    <div className="space-y-4 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">{t("profiles.title")}</h1>
        {canWrite && (
          <Button
            onClick={() => {
              setEditing(null);
              setFormOpen(true);
            }}
          >
            {t("profiles.create")}
          </Button>
        )}
      </div>

      <p className="text-sm text-foreground/70">{t("profiles.intro")}</p>

      {error && (
        <Alert tone="red" onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Input
        className="max-w-xs"
        placeholder={t("profiles.searchPlaceholder")}
        value={search}
        onChange={(event) => {
          setSearch(event.target.value);
          setPage(1);
        }}
      />

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

      <ProfileFormDialog open={formOpen} profile={editing} onClose={() => setFormOpen(false)} />
      <ApplyProfileDialog profile={applying} onClose={() => setApplying(null)} />
    </div>
  );
}
