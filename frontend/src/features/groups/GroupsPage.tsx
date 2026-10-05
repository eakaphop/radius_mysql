import type { ColumnDef } from "@tanstack/react-table";
import { useCallback, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { DataTable } from "@/components/data-table/DataTable";
import { Pagination } from "@/components/data-table/Pagination";
import { Badge, Button, Input } from "@/components/ui/primitives";
import { useIsAdmin } from "@/features/auth/useIsAdmin";
import { GroupFormDialog } from "@/features/groups/GroupFormDialog";
import type { GroupDetail, GroupListItem } from "@/features/groups/groupsApi";
import { groupsApi } from "@/features/groups/groupsApi";
import { useGroupMutations, useGroupsList } from "@/features/groups/useGroups";

const PAGE_SIZE = 25;

function serviceOfGroup(groupname: string): "pppoe" | "hotspot" | "unknown" {
  if (groupname.startsWith("pppoe-")) return "pppoe";
  if (groupname.startsWith("hotspot-")) return "hotspot";
  return "unknown";
}

export function GroupsPage() {
  const { t } = useTranslation();
  const canWrite = useIsAdmin();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<GroupDetail | null>(null);

  const { data, isLoading, isError } = useGroupsList({ search, page, page_size: PAGE_SIZE });
  const { remove } = useGroupMutations();

  const openEdit = useCallback(async (groupname: string) => {
    setEditing(await groupsApi.get(groupname));
    setDialogOpen(true);
  }, []);

  const columns = useMemo<ColumnDef<GroupListItem, unknown>[]>(
    () => [
      { accessorKey: "groupname", header: t("groups.fields.groupname") },
      {
        id: "service",
        header: t("users.fields.serviceType"),
        cell: ({ row }) => (
          <Badge tone="blue">{t(`serviceType.${serviceOfGroup(row.original.groupname)}`)}</Badge>
        ),
      },
      { accessorKey: "member_count", header: t("groups.fields.memberCount") },
      {
        id: "actions",
        header: "",
        cell: ({ row }) =>
          canWrite ? (
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => void openEdit(row.original.groupname)}>
                {t("common.edit")}
              </Button>
              <Button
                variant="danger"
                onClick={() => {
                  if (
                    window.confirm(
                      t("groups.confirmDelete", { groupname: row.original.groupname })
                    )
                  ) {
                    remove.mutate(row.original.groupname);
                  }
                }}
              >
                {t("common.delete")}
              </Button>
            </div>
          ) : null,
      },
    ],
    [t, canWrite, remove, openEdit]
  );

  return (
    <div className="space-y-4 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">{t("groups.title")}</h1>
        {canWrite && (
          <Button
            onClick={() => {
              setEditing(null);
              setDialogOpen(true);
            }}
          >
            {t("groups.create")}
          </Button>
        )}
      </div>

      <Input
        className="max-w-xs"
        placeholder={t("groups.searchPlaceholder")}
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

      <GroupFormDialog open={dialogOpen} group={editing} onClose={() => setDialogOpen(false)} />
    </div>
  );
}
