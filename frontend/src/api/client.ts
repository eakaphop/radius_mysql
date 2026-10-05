/**
 * Base API client. All HTTP calls to the backend go through here — components
 * must never call `fetch` directly (see CLAUDE.md section 6 conventions).
 */

import { getAccessToken } from "@/features/auth/tokenStore";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://10.125.1.251:8001/api/v1";

// Paths that must never trigger a refresh-and-retry on 401, to avoid
// recursing into /auth/refresh from within its own failure handling.
const AUTH_PATHS_EXEMPT_FROM_REFRESH = ["/auth/login", "/auth/refresh"];

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string | undefined,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Set by AuthProvider on mount. Attempts a silent refresh, returns the new
 * access token on success or null on failure. */
let unauthorizedHandler: (() => Promise<string | null>) | null = null;

export function setUnauthorizedHandler(handler: (() => Promise<string | null>) | null): void {
  unauthorizedHandler = handler;
}

export function buildQuery(
  params: Record<string, string | number | boolean | null | undefined>
): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

async function send(path: string, init: RequestInit, isRetry: boolean): Promise<Response> {
  const headers = new Headers(init.headers);
  if (init.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const token = getAccessToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
    credentials: "include",
  });

  const bare = path.split("?")[0];
  if (
    response.status === 401 &&
    !isRetry &&
    unauthorizedHandler &&
    !AUTH_PATHS_EXEMPT_FROM_REFRESH.includes(bare)
  ) {
    const newToken = await unauthorizedHandler();
    if (newToken) {
      return send(path, init, true);
    }
  }
  return response;
}

async function toApiError(response: Response): Promise<ApiError> {
  const body = await response.json().catch(() => ({}));
  const detail = typeof body.detail === "string" ? body.detail : response.statusText;
  return new ApiError(response.status, body.code, detail);
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  const response = await send(path, init, false);
  if (!response.ok) {
    throw await toApiError(response);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

const jsonBody = (body: unknown): string | undefined =>
  body === undefined ? undefined : JSON.stringify(body);

export const apiClient = {
  get: <T>(path: string) => request<T>(path, { method: "GET" }),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: jsonBody(body) }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PUT", body: jsonBody(body) }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: jsonBody(body) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),

  /** Download an authenticated file (e.g. CSV) and hand it to the browser. */
  download: async (path: string, filename: string): Promise<void> => {
    const response = await send(path, { method: "GET" }, false);
    if (!response.ok) {
      throw await toApiError(response);
    }
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  },
};
