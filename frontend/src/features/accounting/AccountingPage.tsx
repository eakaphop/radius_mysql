import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "@/api/client";
import { DataTable } from "@/components/data-table/DataTable";
import { Pagination } from "@/components/data-table/Pagination";
import { Alert, Badge, Button, Dialog, Field, Input } from "@/components/ui/primitives";
import type { AccountingDetail, AccountingFilters, AccountingItem } from "@/features/accounting/accountingApi";
import { accountingApi } from "@/features/accounting/accountingApi";
import {
  daysAgoLocalInput,
  formatBytes,
  formatDateTime,
  formatDuration,
  fromLocalInputValue,
} from "@/lib/format";

const PAGE_SIZE = 50;

interface DraftFilters {
  username: string;
  nasipaddress: string;
  from: string;
  to: string;
}

function toApiFilters(draft: DraftFilters): AccountingFilters {
  return {
    username: draft.username.trim() || undefined,
    nasipaddress: draft.nasipaddress.trim() || undefined,
    from: fromLocalInputValue(draft.from),
    to: fromLocalInputValue(draft.to),
  };
}

const DETAIL_FIELDS: (keyof AccountingDetail)[] = [
  "radacctid",
  "acctsessionid",
  "acctuniqueid",
  "username",
  "nasipaddress",
  "nasportid",
  "nasporttype",
  "servicetype",
  "framedprotocol",
  "framedipaddress",
  "calledstationid",
  "callingstationid",
  "acctstarttime",
  "acctupdatetime",
  "acctstoptime",
  "acctsessiontime",
  "acctinputoctets",
  "acctoutputoctets",
  "acctterminatecause",
];

function renderDetailValue(key: keyof AccountingDetail, detail: AccountingDetail): string {
  const value = detail[key];
  if (key === "acctstarttime" || key === "acctstoptime" || key === "acctupdatetime") {
    return formatDateTime(value as string | null);
  }
  if (key === "acctsessiontime") {
    return formatDuration(value as number | null);
  }
  if (key === "acctinputoctets" || key === "acctoutputoctets") {
    return formatBytes(value as number | null);
  }
  return value === null || value === undefined || value === "" ? "—" : String(value);
}

export function AccountingPage() {
  const { t } = useTranslation();
  const [draft, setDraft] = useState<DraftFilters>({
    username: "",
    nasipaddress: "",
    from: daysAgoLocalInput(7),
    to: "",
  });
  const [filters, setFilters] = useState<AccountingFilters>(() => toApiFilters(draft));
  const [page, setPage] = useState(1);
  const [detailId, setDetailId] = useState<number | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState(false);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["accounting", filters, page],
    queryFn: () => accountingApi.list(filters, page, PAGE_SIZE),
  });

  const detail = useQuery({
    queryKey: ["accounting", "detail", detailId],
    queryFn: () => accountingApi.get(detailId as number),
    enabled: detailId !== null,
  });
  const detailData = detail.data;

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
      { accessorKey: "username", header: t("accounting.fields.username") },
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
      {
        id: "actions",
        header: "",
        cell: ({ row }) => (
          <Button variant="secondary" onClick={() => setDetailId(row.original.radacctid)}>
            {t("common.details")}
          </Button>
        ),
      },
    ],
    [t]
  );

  const exportCsv = async () => {
    setExportError(null);
    setIsExporting(true);
    try {
      await accountingApi.exportCsv(filters);
    } catch (err) {
      setExportError(err instanceof ApiError ? err.message : t("common.unknownError"));
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="space-y-4 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">{t("accounting.title")}</h1>
        <Button variant="secondary" disabled={isExporting} onClick={() => void exportCsv()}>
          {t("accounting.export")}
        </Button>
      </div>

      <form
        className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5"
        onSubmit={(event) => {
          event.preventDefault();
          setFilters(toApiFilters(draft));
          setPage(1);
        }}
      >
        <Field label={t("accounting.fields.username")} htmlFor="acct-username">
          <Input
            id="acct-username"
            value={draft.username}
            onChange={(event) => setDraft({ ...draft, username: event.target.value })}
          />
        </Field>
        <Field label={t("accounting.fields.nasipaddress")} htmlFor="acct-nas">
          <Input
            id="acct-nas"
            value={draft.nasipaddress}
            onChange={(event) => setDraft({ ...draft, nasipaddress: event.target.value })}
          />
        </Field>
        <Field label={t("common.from")} htmlFor="acct-from">
          <Input
            id="acct-from"
            type="datetime-local"
            value={draft.from}
            onChange={(event) => setDraft({ ...draft, from: event.target.value })}
          />
        </Field>
        <Field label={t("common.to")} htmlFor="acct-to">
          <Input
            id="acct-to"
            type="datetime-local"
            value={draft.to}
            onChange={(event) => setDraft({ ...draft, to: event.target.value })}
          />
        </Field>
        <div className="flex items-end">
          <Button type="submit">{t("common.search")}</Button>
        </div>
      </form>
      <p className="text-xs text-foreground/60">{t("accounting.windowHint")}</p>

      {exportError && (
        <Alert tone="red" onDismiss={() => setExportError(null)}>
          {exportError}
        </Alert>
      )}

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
        open={detailId !== null}
        title={t("accounting.detailTitle", { id: detailId ?? "" })}
        onClose={() => setDetailId(null)}
      >
        {detail.isLoading && <p className="text-foreground/60">{t("table.loading")}</p>}
        {detail.isError && <p className="text-red-600">{t("table.error")}</p>}
        {detailData && (
          <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
            {DETAIL_FIELDS.map((key) => (
              <div key={key} className="contents">
                <dt className="text-foreground/60">{t(`accounting.fields.${key}`)}</dt>
                <dd className="break-all">{renderDetailValue(key, detailData)}</dd>
              </div>
            ))}
          </dl>
        )}
      </Dialog>
    </div>
  );
}
