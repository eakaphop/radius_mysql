import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/primitives";

interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ page, pageSize, total, onPageChange }: PaginationProps) {
  const { t } = useTranslation();
  const lastPage = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-foreground/60">{t("table.total", { count: total })}</span>
      <div className="flex items-center gap-2">
        <Button variant="secondary" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
          {t("table.previous")}
        </Button>
        <span>{t("table.pageOf", { page, lastPage })}</span>
        <Button
          variant="secondary"
          disabled={page >= lastPage}
          onClick={() => onPageChange(page + 1)}
        >
          {t("table.next")}
        </Button>
      </div>
    </div>
  );
}
