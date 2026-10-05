import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { DataTable } from "@/components/data-table/DataTable";
import { Alert, Badge, Card } from "@/components/ui/primitives";
import type { EffectiveAttribute } from "@/features/shaping/shapingApi";
import { shapingApi } from "@/features/shaping/shapingApi";

/** Shows what shaping a user actually receives and whether each value comes
 * from the user's own radreply or from one of their groups (CLAUDE.md 6.1). */
export function EffectiveShaping({ username }: { username: string }) {
  const { t } = useTranslation();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["shaping", "effective", username],
    queryFn: () => shapingApi.effective(username),
  });

  const columns = useMemo<ColumnDef<EffectiveAttribute, unknown>[]>(
    () => [
      { accessorKey: "attribute", header: t("attributes.attribute") },
      { accessorKey: "op", header: t("attributes.operator") },
      {
        id: "value",
        header: t("attributes.value"),
        cell: ({ row }) => <code className="text-xs">{row.original.value}</code>,
      },
      {
        id: "source",
        header: t("shaping.effective.source"),
        cell: ({ row }) =>
          row.original.source === "user" ? (
            <Badge tone="amber">{t("shaping.effective.fromUser")}</Badge>
          ) : (
            <Badge tone="blue">
              {t("shaping.effective.fromGroup", {
                group: row.original.source.replace(/^group:/, ""),
              })}
            </Badge>
          ),
      },
    ],
    [t]
  );

  return (
    <div className="space-y-4">
      <p className="text-sm text-foreground/70">{t("shaping.effective.explanation")}</p>

      {data?.warnings.map((warning) => (
        <Alert key={warning}>
          {t("shaping.effective.multipleShapingGroups", {
            service: t(`serviceType.${warning.split(":")[1] ?? "unknown"}`),
          })}
        </Alert>
      ))}

      <Card title={t("shaping.effective.assignedProfiles")}>
        {data && data.profiles.length === 0 && (
          <p className="text-sm text-foreground/60">{t("shaping.effective.noProfiles")}</p>
        )}
        <ul className="space-y-1 text-sm">
          {data?.profiles.map((profile) => (
            <li key={`${profile.target_type}:${profile.target_name}`}>
              <span className="font-medium">{profile.profile_name}</span> —{" "}
              {t(`shaping.effective.assignedVia.${profile.target_type}`, {
                name: profile.target_name,
              })}
            </li>
          ))}
        </ul>
      </Card>

      <DataTable
        columns={columns}
        data={data?.effective ?? []}
        isLoading={isLoading}
        isError={isError}
      />
    </div>
  );
}
