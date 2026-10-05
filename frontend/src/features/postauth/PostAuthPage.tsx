import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { DataTable } from "@/components/data-table/DataTable";
import { Pagination } from "@/components/data-table/Pagination";
import { Badge, Button, Field, Input, Select } from "@/components/ui/primitives";
import type { PostAuthFilters, PostAuthItem, PostAuthReply } from "@/features/postauth/postauthApi";
import { postauthApi } from "@/features/postauth/postauthApi";
import { daysAgoLocalInput, formatDateTime, fromLocalInputValue } from "@/lib/format";

const PAGE_SIZE = 25;

interface DraftFilters {
  username: string;
  reply: PostAuthReply | "";
  from: string;
  to: string;
}

export function PostAuthPage() {
  const { t } = useTranslation();
  const [draft, setDraft] = useState<DraftFilters>({
    username: "",
    reply: "",
    from: daysAgoLocalInput(1),
    to: "",
  });
  const [filters, setFilters] = useState<PostAuthFilters>({
    username: undefined,
    reply: "",
    from: fromLocalInputValue(draft.from),
    to: undefined,
  });
  const [page, setPage] = useState(1);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["postauth", filters, page],
    queryFn: () => postauthApi.list(filters, page, PAGE_SIZE),
  });

  const columns = useMemo<ColumnDef<PostAuthItem, unknown>[]>(
    () => [
      {
        id: "authdate",
        header: t("postauth.fields.authdate"),
        cell: ({ row }) => formatDateTime(row.original.authdate),
      },
      { accessorKey: "username", header: t("postauth.fields.username") },
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
    <div className="space-y-4 p-6">
      <h1 className="text-xl font-semibold">{t("postauth.title")}</h1>

      <form
        className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5"
        onSubmit={(event) => {
          event.preventDefault();
          setFilters({
            username: draft.username.trim() || undefined,
            reply: draft.reply,
            from: fromLocalInputValue(draft.from),
            to: fromLocalInputValue(draft.to),
          });
          setPage(1);
        }}
      >
        <Field label={t("postauth.fields.username")} htmlFor="pa-username">
          <Input
            id="pa-username"
            value={draft.username}
            onChange={(event) => setDraft({ ...draft, username: event.target.value })}
          />
        </Field>
        <Field label={t("postauth.fields.reply")} htmlFor="pa-reply">
          <Select
            id="pa-reply"
            className="w-full"
            value={draft.reply}
            onChange={(event) => setDraft({ ...draft, reply: event.target.value as PostAuthReply | "" })}
          >
            <option value="">{t("postauth.allReplies")}</option>
            <option value="Access-Accept">Access-Accept</option>
            <option value="Access-Reject">Access-Reject</option>
          </Select>
        </Field>
        <Field label={t("common.from")} htmlFor="pa-from">
          <Input
            id="pa-from"
            type="datetime-local"
            value={draft.from}
            onChange={(event) => setDraft({ ...draft, from: event.target.value })}
          />
        </Field>
        <Field label={t("common.to")} htmlFor="pa-to">
          <Input
            id="pa-to"
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
    </div>
  );
}
