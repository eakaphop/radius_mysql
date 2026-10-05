import type { Paginated } from "@/api/client";
import { apiClient, buildQuery } from "@/api/client";

export interface AccountingItem {
  radacctid: number;
  acctsessionid: string;
  username: string | null;
  nasipaddress: string;
  nasporttype: string | null;
  framedipaddress: string | null;
  callingstationid: string | null;
  acctstarttime: string | null;
  acctstoptime: string | null;
  acctsessiontime: number | null;
  /** Octets the NAS received from the user = upload. */
  acctinputoctets: number | null;
  /** Octets the NAS sent to the user = download. */
  acctoutputoctets: number | null;
  acctterminatecause: string | null;
}

export interface AccountingDetail extends AccountingItem {
  acctuniqueid: string;
  nasportid: string | null;
  calledstationid: string | null;
  servicetype: string | null;
  framedprotocol: string | null;
  acctupdatetime: string | null;
}

export interface AccountingFilters {
  username?: string;
  nasipaddress?: string;
  from?: string;
  to?: string;
}

export const accountingApi = {
  list: (filters: AccountingFilters, page: number, pageSize: number) =>
    apiClient.get<Paginated<AccountingItem>>(
      `/accounting${buildQuery({ ...filters, page, page_size: pageSize })}`
    ),
  get: (radacctid: number) => apiClient.get<AccountingDetail>(`/accounting/${radacctid}`),
  exportCsv: (filters: AccountingFilters) =>
    apiClient.download(
      `/accounting/export${buildQuery({ ...filters })}`,
      `accounting-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}.csv`
    ),
};
