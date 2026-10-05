import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "@/api/client";
import { DataTable } from "@/components/data-table/DataTable";
import { Pagination } from "@/components/data-table/Pagination";
import { Alert, Badge, Button, Tabs } from "@/components/ui/primitives";
import { useIsAdmin } from "@/features/auth/useIsAdmin";
import { CoaDialog } from "@/features/sessions/CoaDialog";
import type { DynAuthResult, OnlineSession, SessionService } from "@/features/sessions/sessionsApi";
import { sessionsApi } from "@/features/sessions/sessionsApi";
import { formatBytes, formatDateTime, formatDuration } from "@/lib/format";

const PAGE_SIZE = 25;
const AUTO_REFRESH_MS = 15_000;

export function SessionsPage() {
  const { t } = useTranslation();
  const canWrite = useIsAdmin();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<SessionService>("all");
  const [page, setPage] = useState(1);
  const [coaSession, setCoaSession] = useState<OnlineSession | null>(null);
  const [lastResult, setLastResult] = useState<{ tone: string; text: string } | null>(null);

  const capabilities = useQuery({
    queryKey: ["sessions", "capabilities"],
    queryFn: sessionsApi.capabilities,
  });

  const { data, isLoading, isError } = useQuery({
    queryKey: ["sessions", "online", tab, page],
    queryFn: () => sessionsApi.online(tab, page, PAGE_SIZE),
    refetchInterval: AUTO_REFRESH_MS,
  });

  useEffect(() => {
    setPage(1);
  }, [tab]);

  const showResult = useCallback((result: DynAuthResult) => {
    setLastResult({
      tone: result.success ? "green" : "red",
      text: result.detail,
    });
  }, []);

  const disconnect = useCallback(
    async (session: OnlineSession) => {
      if (
        !window.confirm(t("sessions.confirmDisconnect", { username: session.username ?? "" }))
      ) {
        return;
      }
      try {
        showResult(await sessionsApi.disconnect(session.radacctid));
        await queryClient.invalidateQueries({ queryKey: ["sessions"] });
      } catch (err) {
        setLastResult({
          tone: "red",
          text: err instanceof ApiError ? err.message : t("common.unknownError"),
        });
      }
    },
    [t, queryClient, showResult]
  );

  const columns = useMemo<ColumnDef<OnlineSession, unknown>[]>(
    () => [
      { accessorKey: "username", header: t("accounting.fields.username") },
      {
        id: "service_type",
        header: t("users.fields.serviceType"),
        cell: ({ row }) => <Badge tone="blue">{t(`serviceType.${row.original.service_type}`)}</Badge>,
      },
      { accessorKey: "nasipaddress", header: t("accounting.fields.nasipaddress") },
      { accessorKey: "framedipaddress", header: t("accounting.fields.framedipaddress") },
      {
        id: "start",
        header: t("accounting.fields.acctstarttime"),
        cell: ({ row }) => formatDateTime(row.original.acctstarttime),
      },
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
      {
        id: "actions",
        header: "",
        cell: ({ row }) =>
          canWrite ? (
            <div className="flex justify-end gap-2">
              {capabilities.data?.coa_enabled && (
                <Button variant="secondary" onClick={() => setCoaSession(row.original)}>
                  {t("sessions.changeSpeed")}
                </Button>
              )}
              {capabilities.data?.pod_enabled && (
                <Button variant="danger" onClick={() => void disconnect(row.original)}>
                  {t("sessions.disconnect")}
                </Button>
              )}
            </div>
          ) : null,
      },
    ],
    [t, canWrite, capabilities.data, disconnect]
  );

  return (
    <div className="space-y-4 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">{t("sessions.title")}</h1>
        <span className="text-xs text-foreground/60">{t("sessions.autoRefresh")}</span>
      </div>

      {capabilities.data && !capabilities.data.pod_enabled && !capabilities.data.coa_enabled && (
        <Alert>{t("sessions.featuresDisabled")}</Alert>
      )}
      {lastResult && (
        <Alert tone={lastResult.tone} onDismiss={() => setLastResult(null)}>
          {lastResult.text}
        </Alert>
      )}

      <Tabs
        tabs={[
          { id: "all" as SessionService, label: t("sessions.tabs.all") },
          { id: "pppoe" as SessionService, label: t("sessions.tabs.pppoe") },
          { id: "hotspot" as SessionService, label: t("sessions.tabs.hotspot") },
        ]}
        active={tab}
        onChange={setTab}
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

      <CoaDialog session={coaSession} onClose={() => setCoaSession(null)} onResult={showResult} />
    </div>
  );
}
