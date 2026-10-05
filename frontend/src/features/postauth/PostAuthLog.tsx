import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { DataTable } from "@/components/data-table/DataTable";
import { Pagination } from "@/components/data-table/Pagination";
import { Badge } from "@/components/ui/primitives";
import type { PostAuthItem } from "@/features/postauth/postauthApi";
import { postauthApi } from "@/features/postauth/postauthApi";
import { formatDateTime } from "@/lib/format";

const PAGE_SIZE = 25;

/** Auth log scoped to one user — used as the User detail "Auth log" tab. */
export function PostAuthLog({ username }: { username: string }) {
  const { t } = useTranslation();
  const [page, setPage] = useState(1);
  const { data, isLoading, isError } = useQuery({
    queryKey: ["postauth", { username }, page],
    queryFn: () => postauthApi.list({ username }, page, PAGE_SIZE),
  });

  const columns = useMemo<ColumnDef<PostAuthItem, unknown>[]>(
    () => [
      {
        id: "authdate",
        header: t("postauth.fields.authdate"),
        cell: ({ row }) => formatDateTime(row.original.authdate),
      },
      {
        id: "reply",
        header: t("postauth.fields.reply"),
        cell: ({ row }) => (
          <Badge tone={row.original.reply === "Access-Accept" ? "green" : "red"}>
            {row.original.reply}
          </Badge>
        ),
      },
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
