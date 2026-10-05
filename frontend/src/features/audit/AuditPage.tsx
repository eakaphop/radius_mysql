import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { DataTable } from "@/components/data-table/DataTable";
import { Pagination } from "@/components/data-table/Pagination";
import { Button, Dialog, Field, Input } from "@/components/ui/primitives";
import type { AuditFilters, AuditItem } from "@/features/audit/auditApi";
import { auditApi } from "@/features/audit/auditApi";
import { daysAgoLocalInput, formatDateTime, fromLocalInputValue } from "@/lib/format";

const PAGE_SIZE = 25;

interface DraftFilters {
  admin: string;
  resource_type: string;
  from: string;
  to: string;
}

export function AuditPage() {
  const { t } = useTranslation();
  const [draft, setDraft] = useState<DraftFilters>({
    admin: "",
    resource_type: "",
    from: daysAgoLocalInput(7),
    to: "",
  });
  const [filters, setFilters] = useState<AuditFilters>({ from: fromLocalInputValue(draft.from) });
  const [page, setPage] = useState(1);
  const [detail, setDetail] = useState<AuditItem | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["audit", filters, page],
    queryFn: () => auditApi.list(filters, page, PAGE_SIZE),
  });

  const columns = useMemo<ColumnDef<AuditItem, unknown>[]>(
    () => [
      {
        id: "created_at",
        header: t("audit.fields.createdAt"),
        cell: ({ row }) => formatDateTime(row.original.created_at),
      },
      { accessorKey: "admin_username", header: t("audit.fields.admin") },
      { accessorKey: "action", header: t("audit.fields.action") },
      { accessorKey: "resource_type", header: t("audit.fields.resourceType") },
      { accessorKey: "resource_id", header: t("audit.fields.resourceId") },
      { accessorKey: "ip_address", header: t("audit.fields.ipAddress") },
      {
        id: "actions",
        header: "",
        cell: ({ row }) => (
          <Button variant="secondary" onClick={() => setDetail(row.original)}>
            {t("common.details")}
          </Button>
        ),
      },
    ],
    [t]
  );

  return (
    <div className="space-y-4 p-6">
      <h1 className="text-xl font-semibold">{t("audit.title")}</h1>

      <form
        className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5"
        onSubmit={(event) => {
          event.preventDefault();
          setFilters({
            admin: draft.admin.trim() || undefined,
            resource_type: draft.resource_type.trim() || undefined,
            from: fromLocalInputValue(draft.from),
            to: fromLocalInputValue(draft.to),
          });
          setPage(1);
        }}
      >
        <Field label={t("audit.fields.admin")} htmlFor="audit-admin">
          <Input
            id="audit-admin"
            value={draft.admin}
            onChange={(event) => setDraft({ ...draft, admin: event.target.value })}
          />
        </Field>
        <Field label={t("audit.fields.resourceType")} htmlFor="audit-resource-type">
          <Input
            id="audit-resource-type"
            placeholder="radius_user, nas, shaping_profile, auth, ..."
            value={draft.resource_type}
            onChange={(event) => setDraft({ ...draft, resource_type: event.target.value })}
          />
        </Field>
        <Field label={t("common.from")} htmlFor="audit-from">
          <Input
            id="audit-from"
            type="datetime-local"
            value={draft.from}
            onChange={(event) => setDraft({ ...draft, from: event.target.value })}
          />
        </Field>
        <Field label={t("common.to")} htmlFor="audit-to">
          <Input
            id="audit-to"
            type="datetime-local"
            value={draft.to}
            onChange={(event) => setDraft({ ...draft, to: event.target.value })}
          />
        </Field>
        <div className="flex items-end">
          <Button type="submit">{t("common.search")}</Button>
        </div>
      </form>

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

      <Dialog
        open={detail !== null}
        title={t("audit.detailTitle", { id: detail?.id ?? "" })}
        onClose={() => setDetail(null)}
      >
        {detail && (
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <p className="mb-1 text-xs font-medium text-foreground/60">{t("audit.before")}</p>
              <pre className="overflow-x-auto rounded bg-foreground/5 p-2 text-xs">
                {detail.before_json ? JSON.stringify(detail.before_json, null, 2) : "—"}
              </pre>
            </div>
            <div>
              <p className="mb-1 text-xs font-medium text-foreground/60">{t("audit.after")}</p>
              <pre className="overflow-x-auto rounded bg-foreground/5 p-2 text-xs">
                {detail.after_json ? JSON.stringify(detail.after_json, null, 2) : "—"}
              </pre>
            </div>
          </div>
        )}
      </Dialog>
    </div>
  );
}
