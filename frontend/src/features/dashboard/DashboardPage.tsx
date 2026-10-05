import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { DataTable } from "@/components/data-table/DataTable";
import { Badge, Card } from "@/components/ui/primitives";
import { AuthStatsChart } from "@/features/dashboard/AuthStatsChart";
import { dashboardApi } from "@/features/dashboard/dashboardApi";
import { StatTile } from "@/features/dashboard/StatTile";
import { TrafficChart } from "@/features/dashboard/TrafficChart";
import type { OnlineSession } from "@/features/sessions/sessionsApi";
import { sessionsApi } from "@/features/sessions/sessionsApi";
import { formatBytes, formatDateTime } from "@/lib/format";

const TRAFFIC_DAYS = 7;
const AUTH_HOURS = 24;
const RECENT_SESSIONS = 10;

export function DashboardPage() {
  const { t } = useTranslation();

  const summary = useQuery({ queryKey: ["dashboard", "summary"], queryFn: dashboardApi.summary });
  const traffic = useQuery({
    queryKey: ["dashboard", "traffic", TRAFFIC_DAYS],
    queryFn: () => dashboardApi.traffic(TRAFFIC_DAYS),
  });
  const authStats = useQuery({
    queryKey: ["dashboard", "auth-stats", AUTH_HOURS],
    queryFn: () => dashboardApi.authStats(AUTH_HOURS),
  });
  const recentSessions = useQuery({
    queryKey: ["dashboard", "recent-sessions"],
    queryFn: () => sessionsApi.online("all", 1, RECENT_SESSIONS),
  });

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
    ],
    [t]
  );

  return (
    <div className="space-y-6 p-6">
      <h1 className="text-xl font-semibold">{t("dashboard.title")}</h1>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label={t("dashboard.stats.totalUsers")} value={String(summary.data?.total_users ?? "—")} />
        <StatTile
          label={t("dashboard.stats.online")}
          value={String(summary.data?.online_users ?? "—")}
          hint={t("dashboard.stats.onlineSessions", { count: summary.data?.online_sessions ?? 0 })}
        />
        <StatTile
          label={t("dashboard.stats.auth24h")}
          value={`${summary.data?.auth_accept_24h ?? "—"} / ${summary.data?.auth_reject_24h ?? "—"}`}
          hint={t("dashboard.stats.acceptReject")}
        />
        <StatTile
          label={t("dashboard.stats.trafficToday")}
          value={formatBytes(
            (summary.data?.traffic_today_download_bytes ?? 0) +
              (summary.data?.traffic_today_upload_bytes ?? 0)
          )}
          hint={`${t("dashboard.traffic.download")} ${formatBytes(summary.data?.traffic_today_download_bytes)} · ${t("dashboard.traffic.upload")} ${formatBytes(summary.data?.traffic_today_upload_bytes)}`}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title={t("dashboard.traffic.title", { days: TRAFFIC_DAYS })}>
          {traffic.data && <TrafficChart data={traffic.data} />}
        </Card>
        <Card title={t("dashboard.auth.title", { hours: AUTH_HOURS })}>
          {authStats.data && <AuthStatsChart data={authStats.data} />}
        </Card>
      </div>

      <Card title={t("dashboard.recentSessions")}>
        <DataTable
          columns={columns}
          data={recentSessions.data?.items ?? []}
          isLoading={recentSessions.isLoading}
          isError={recentSessions.isError}
        />
      </Card>
    </div>
  );
}
