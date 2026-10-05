import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { useCallback, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "@/api/client";
import { DataTable } from "@/components/data-table/DataTable";
import { Pagination } from "@/components/data-table/Pagination";
import { Alert, Button, Card, Input } from "@/components/ui/primitives";
import { useIsAdmin } from "@/features/auth/useIsAdmin";
import type { Nas } from "@/features/nas/nasApi";
import { nasApi } from "@/features/nas/nasApi";
import { NasFormDialog } from "@/features/nas/NasFormDialog";

const PAGE_SIZE = 25;
const MIKROTIK_COA_COMMAND = "/radius incoming set accept=yes port=3799";

export function NasPage() {
  const { t } = useTranslation();
  const canWrite = useIsAdmin();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Nas | null>(null);
  const [showReloadWarning, setShowReloadWarning] = useState(false);
  const [revealed, setRevealed] = useState<Record<number, string>>({});
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["nas", search, page],
    queryFn: () => nasApi.list({ search, page, page_size: PAGE_SIZE }),
  });

  const afterWrite = useCallback(async () => {
    setShowReloadWarning(true);
    setRevealed({});
    await queryClient.invalidateQueries({ queryKey: ["nas"] });
  }, [queryClient]);

  const openEdit = useCallback(async (id: number) => {
    setError(null);
    try {
      setEditing(await nasApi.get(id, true));
      setDialogOpen(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("common.unknownError"));
    }
  }, [t]);

  const reveal = useCallback(async (id: number) => {
    const nas = await nasApi.get(id, true);
    setRevealed((current) => ({ ...current, [id]: nas.secret }));
  }, []);

  const remove = useCallback(
    async (nas: Nas) => {
      if (!window.confirm(t("nas.confirmDelete", { name: nas.shortname ?? nas.nasname }))) {
        return;
      }
      setError(null);
      try {
        await nasApi.remove(nas.id);
        await afterWrite();
      } catch (err) {
        setError(err instanceof ApiError ? err.message : t("common.unknownError"));
      }
    },
    [t, afterWrite]
  );

  const columns = useMemo<ColumnDef<Nas, unknown>[]>(
    () => [
      { accessorKey: "shortname", header: t("nas.fields.shortname") },
      { accessorKey: "nasname", header: t("nas.fields.nasname") },
      { accessorKey: "type", header: t("nas.fields.type") },
      { accessorKey: "description", header: t("nas.fields.description") },
      {
        id: "secret",
        header: t("nas.fields.secret"),
        cell: ({ row }) => (
          <div className="flex items-center gap-2">
            <code className="text-xs">{revealed[row.original.id] ?? row.original.secret}</code>
            {canWrite && revealed[row.original.id] === undefined && (
              <button
                type="button"
                className="text-xs text-primary hover:underline"
                onClick={() => void reveal(row.original.id)}
              >
                {t("nas.reveal")}
              </button>
            )}
          </div>
        ),
      },
      {
        id: "actions",
        header: "",
        cell: ({ row }) =>
          canWrite ? (
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => void openEdit(row.original.id)}>
                {t("common.edit")}
              </Button>
              <Button variant="danger" onClick={() => void remove(row.original)}>
                {t("common.delete")}
              </Button>
            </div>
          ) : null,
      },
    ],
    [t, canWrite, revealed, reveal, openEdit, remove]
  );

  return (
    <div className="space-y-4 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">{t("nas.title")}</h1>
        {canWrite && (
          <Button
            onClick={() => {
              setEditing(null);
              setDialogOpen(true);
            }}
          >
            {t("nas.create")}
          </Button>
        )}
      </div>

      {showReloadWarning && (
        <Alert onDismiss={() => setShowReloadWarning(false)}>{t("nas.reloadWarning")}</Alert>
      )}
      {error && (
        <Alert tone="red" onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Card title={t("nas.helpTitle")}>
        <p className="mb-2 text-sm text-foreground/70">{t("nas.helpText")}</p>
        <pre className="overflow-x-auto rounded bg-foreground/5 px-3 py-2 text-xs">
          {MIKROTIK_COA_COMMAND}
        </pre>
      </Card>

      <Input
        className="max-w-xs"
        placeholder={t("nas.searchPlaceholder")}
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

      <NasFormDialog
        open={dialogOpen}
        nas={editing}
        onClose={() => setDialogOpen(false)}
        onSaved={() => {
          setDialogOpen(false);
          void afterWrite();
        }}
      />
    </div>
  );
}
