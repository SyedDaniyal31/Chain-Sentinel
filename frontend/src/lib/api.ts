import type {
  ApiErrorBody,
  ChainListResponse,
  PaginatedScanResponse,
  ScanCreateRequest,
  ScanCreateResponse,
  ScanJob,
  ScanSummaryResponse,
} from "@/types/scan";
import { ApiError } from "@/types/scan";

const DEFAULT_API_URL = "http://localhost:8000";

/** Resolved once at module load; exposed for debugging in the browser console. */
export function getApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim().replace(/\/$/, "");
  return configured && configured.length > 0 ? configured : DEFAULT_API_URL;
}

if (typeof window !== "undefined") {
  console.info("[ChainSentinel API] NEXT_PUBLIC_API_URL:", process.env.NEXT_PUBLIC_API_URL ?? "(unset)");
  console.info("[ChainSentinel API] Resolved base URL:", getApiBaseUrl());
}

async function apiFetch(url: string, init?: RequestInit): Promise<Response> {
  const method = init?.method ?? "GET";
  console.debug("[ChainSentinel API] Request:", method, url);

  let response: Response;
  try {
    response = await fetch(url, init);
  } catch (error) {
    console.error("[ChainSentinel API] Network failure:", method, url, error);
    throw error;
  }

  console.debug("[ChainSentinel API] Response status:", method, url, response.status);

  if (!response.ok) {
    const errorBody = await response.clone().text();
    console.error("[ChainSentinel API] Error body:", method, url, response.status, errorBody);
  }

  return response;
}

async function parseError(response: Response): Promise<ApiError> {
  let body: ApiErrorBody | undefined;
  try {
    body = (await response.json()) as ApiErrorBody;
  } catch {
    body = undefined;
  }

  const detail = body?.detail;
  let message = `Request failed (${response.status})`;

  if (typeof detail === "string") {
    message = detail;
  } else if (Array.isArray(detail) && detail.length > 0) {
    message = detail.map((item) => item.msg).join("; ");
  } else if (body?.error_code) {
    message = typeof detail === "string" ? detail : `Request failed (${body.error_code})`;
  }

  return new ApiError(message, response.status, body);
}

export async function createScan(payload: ScanCreateRequest): Promise<ScanCreateResponse> {
  const url = `${getApiBaseUrl()}/api/v1/scans`;
  const response = await apiFetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as ScanCreateResponse;
}

export async function getScan(scanId: number): Promise<ScanJob> {
  const url = `${getApiBaseUrl()}/api/v1/scans/${scanId}`;
  const response = await apiFetch(url, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as ScanJob;
}

export interface GetScansParams {
  page?: number;
  page_size?: number;
}

export async function getScans(params: GetScansParams = {}): Promise<PaginatedScanResponse> {
  const search = new URLSearchParams();
  search.set("page", String(params.page ?? 1));
  search.set("page_size", String(params.page_size ?? 20));

  const url = `${getApiBaseUrl()}/api/v1/scans?${search.toString()}`;
  const response = await apiFetch(url, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as PaginatedScanResponse;
}

export async function getChains(): Promise<ChainListResponse> {
  const url = `${getApiBaseUrl()}/api/v1/chains`;
  const response = await apiFetch(url, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as ChainListResponse;
}

export async function getScanSummary(): Promise<ScanSummaryResponse> {
  const url = `${getApiBaseUrl()}/api/v1/scans/summary`;
  const response = await apiFetch(url, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as ScanSummaryResponse;
}

export function getApiHealthUrl(): string {
  return `${getApiBaseUrl()}/health`;
}
