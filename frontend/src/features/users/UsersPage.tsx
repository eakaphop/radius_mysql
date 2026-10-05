import type { ColumnDef } from "@tanstack/react-table";
import { useCallback, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { DataTable } from "@/components/data-table/DataTable";
import { Pagination } from "@/components/data-table/Pagination";
import { Badge, Button, Input, Select } from "@/components/ui/primitives";
import { useIsAdmin } from "@/features/auth/useIsAdmin";
import { ChangePasswordDialog } from "@/features/users/ChangePasswordDialog";
import { useUserMutations, useUsersList } from "@/features/users/useUsers";
import { UserFormDialog } from "@/features/users/UserFormDialog";
import type { UserDetail, UserListItem, UserStatus } from "@/features/users/usersApi";
import { usersApi } from "@/features/users/usersApi";
import { STATUS_TONES } from "@/features/users/userStatus";
import { formatDateTime } from "@/lib/format";

const PAGE_SIZE = 25;

export function UsersPage() {
  const { t } = useTranslation();
  const canWrite = useIsAdmin();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<UserStatus | "">("");
  const [group, setGroup] = useState("");
  const [page, setPage] = useState(1);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<UserDetail | null>(null);
  const [passwordUsername, setPasswordUsername] = useState<string | null>(null);

  const { data, isLoading, isError } = useUsersList({
    search,
    status,
    group,
    page,
    page_size: PAGE_SIZE,
  });
  const { setStatus: setStatusMutation, remove } = useUserMutations();

  const openEdit = useCallback(async (username: string) => {
    setEditing(await usersApi.get(username));
    setDialogOpen(true);
  }, []);

  const columns = useMemo<ColumnDef<UserListItem, unknown>[]>(
    () => [
      {
        id: "username",
        header: t("users.fields.username"),
        cell: ({ row }) => (
          <Link
            to={`/users/${encodeURIComponent(row.original.username)}`}
            className="text-primary hover:underline"
          >
            {row.original.username}
          </Link>
        ),
      },
      {
        id: "status",
        header: t("users.fields.status"),
        cell: ({ row }) => (
          <Badge tone={STATUS_TONES[row.original.status]}>
            {t(`users.status.${row.original.status}`)}
          </Badge>
        ),
      },
      {
        id: "service_type",
        header: t("users.fields.serviceType"),
        cell: ({ row }) => <Badge tone="blue">{t(`serviceType.${row.original.service_type}`)}</Badge>,
      },
      {
        id: "groups",
        header: t("users.fields.groups"),
        cell: ({ row }) => row.original.groups.join(", ") || "—",
      },
      {
        id: "expiration",
        header: t("users.fields.expiration"),
        cell: ({ row }) => formatDateTime(row.original.expiration),
      },
      {
        id: "actions",
        header: "",
        cell: ({ row }) =>
          canWrite ? (
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => void openEdit(row.original.username)}>
                {t("common.edit")}
              </Button>
              <Button
                variant="secondary"
                onClick={() => setPasswordUsername(row.original.username)}
              >
                {t("users.changePassword")}
              </Button>
              <Button
                variant="secondary"
                onClick={() =>
                  setStatusMutation.mutate({
                    username: row.original.username,
                    enabled: row.original.status === "disabled",
                  })
                }
              >
                {row.original.status === "disabled" ? t("users.enable") : t("users.disable")}
              </Button>
              <Button
                variant="danger"
                onClick={() => {
                  if (
                    window.confirm(t("users.confirmDelete", { username: row.original.username }))
                  ) {
                    remove.mutate(row.original.username);
                  }
                }}
              >
                {t("common.delete")}
              </Button>
            </div>
          ) : null,
      },
    ],
    [t, canWrite, setStatusMutation, remove, openEdit]
  );

  return (
    <div className="space-y-4 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">{t("users.title")}</h1>
        {canWrite && (
          <Button
            onClick={() => {
              setEditing(null);
              setDialogOpen(true);
            }}
          >
            {t("users.create")}
          </Button>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Input
          className="max-w-xs"
          placeholder={t("users.searchPlaceholder")}
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            setPage(1);
          }}
        />
        <Input
          className="max-w-xs"
          placeholder={t("users.groupFilterPlaceholder")}
          value={group}
          onChange={(event) => {
            setGroup(event.target.value);
            setPage(1);
          }}
        />
        <Select
          value={status}
          onChange={(event) => {
            setStatus(event.target.value as UserStatus | "");
            setPage(1);
          }}
        >
          <option value="">{t("users.status.all")}</option>
          <option value="active">{t("users.status.active")}</option>
          <option value="disabled">{t("users.status.disabled")}</option>
          <option value="expired">{t("users.status.expired")}</option>
        </Select>
      </div>

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

      <UserFormDialog open={dialogOpen} user={editing} onClose={() => setDialogOpen(false)} />
      <ChangePasswordDialog
        username={passwordUsername}
        onClose={() => setPasswordUsername(null)}
      />
    </div>
  );
}
