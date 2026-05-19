import { uuid } from "@/lib/uuid";
import type { ApiError, Envelope } from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "https://api.agentinder.io/v1";

export class ApiErrorClass extends Error {
  code: string;
  details?: Record<string, unknown>;
  status?: number;
  constructor(err: ApiError, status?: number) {
    super(err.message);
    this.name = "ApiError";
    this.code = err.code;
    this.details = err.details;
    this.status = status;
  }
}

type RequestOptions = RequestInit & {
  query?: Record<string, string | number | boolean | string[] | undefined>;
};

let authTokenGetter: () => string | null = () => null;
export function setAuthTokenGetter(fn: () => string | null): void {
  authTokenGetter = fn;
}

function buildQuery(params?: RequestOptions["query"]): string {
  if (!params) return "";
  const usp = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) continue;
    if (Array.isArray(value)) {
      if (value.length > 0) usp.set(key, value.join(","));
    } else {
      usp.set(key, String(value));
    }
  }
  const qs = usp.toString();
  return qs ? `?${qs}` : "";
}

export async function apiFetch<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { query, headers, ...rest } = opts;
  const url = `${BASE_URL}${path}${buildQuery(query)}`;

  const finalHeaders = new Headers(headers);
  if (!finalHeaders.has("Content-Type") && rest.body && !(rest.body instanceof FormData)) {
    finalHeaders.set("Content-Type", "application/json");
  }
  finalHeaders.set("Accept", "application/json");

  const token = authTokenGetter();
  if (token) finalHeaders.set("Authorization", `Bearer ${token}`);

  const method = (rest.method ?? "GET").toUpperCase();
  if (method === "POST" || method === "PATCH" || method === "PUT" || method === "DELETE") {
    if (!finalHeaders.has("X-Idempotency-Key")) {
      finalHeaders.set("X-Idempotency-Key", uuid());
    }
  }

  const res = await fetch(url, { ...rest, headers: finalHeaders });
  // 204 No Content
  if (res.status === 204) return undefined as T;

  let body: Envelope<T>;
  try {
    body = (await res.json()) as Envelope<T>;
  } catch {
    throw new ApiErrorClass(
      { code: "INVALID_JSON", message: `Non-JSON response (status ${res.status})` },
      res.status,
    );
  }

  if (!res.ok || body.error) {
    const err = body.error ?? {
      code: `HTTP_${res.status}`,
      message: `Request failed: ${res.statusText}`,
    };
    throw new ApiErrorClass(err, res.status);
  }

  return body.data as T;
}

export const api = {
  get: <T>(path: string, opts?: RequestOptions) => apiFetch<T>(path, { ...opts, method: "GET" }),
  post: <T, B = unknown>(path: string, body?: B, opts?: RequestOptions) =>
    apiFetch<T>(path, {
      ...opts,
      method: "POST",
      body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
    }),
  put: <T, B = unknown>(path: string, body?: B, opts?: RequestOptions) =>
    apiFetch<T>(path, {
      ...opts,
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
    }),
  patch: <T, B = unknown>(path: string, body?: B, opts?: RequestOptions) =>
    apiFetch<T>(path, {
      ...opts,
      method: "PATCH",
      body: body ? JSON.stringify(body) : undefined,
    }),
  delete: <T>(path: string, opts?: RequestOptions) =>
    apiFetch<T>(path, { ...opts, method: "DELETE" }),
};
