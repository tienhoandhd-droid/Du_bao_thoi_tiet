import { buildWebhookUrl, getPublicEnv, normalizeBaseUrl } from "@/lib/env";
import type {
  AssistantQueryRequest,
  AssistantQueryResponse,
  AuditEntry,
  DashboardHealthResponse,
  DocumentSearchRequest,
  DocumentSearchResponse,
  RagQueryRequest,
  RagQueryResponse,
} from "@/types/api";

export const WEBHOOK_BASE = normalizeBaseUrl(getPublicEnv().webhookBase);

export const apiEndpoints = {
  health: buildWebhookUrl("/health"),
  ragQuery: buildWebhookUrl("/rag-query"),
  assistantQuery: buildWebhookUrl("/assistant-query"),
  ingestDocument: buildWebhookUrl("/ingest-document"),
  searchDocs: buildWebhookUrl("/search-docs"),
  approveDocument: buildWebhookUrl("/approve-document"),
} as const;

export type ApiEndpointKey = keyof typeof apiEndpoints;
export type ApiRequestBody =
  | RagQueryRequest
  | AssistantQueryRequest
  | DocumentSearchRequest
  | Record<string, unknown>
  | undefined;

export interface ApiCallOptions<Body = ApiRequestBody> {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: Body;
  token?: string;
  headers?: HeadersInit;
  signal?: AbortSignal;
}

export class ApiError extends Error {
  status: number;
  payload?: { error?: string; message?: string };

  constructor(
    message: string,
    status: number,
    payload?: { error?: string; message?: string },
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

function resolveUrl(endpoint: ApiEndpointKey | string): string {
  return endpoint in apiEndpoints
    ? apiEndpoints[endpoint as ApiEndpointKey]
    : buildWebhookUrl(endpoint);
}

async function parseJson<T>(response: Response): Promise<T> {
  const text = await response.text();
  if (!text) return {} as T;
  try {
    return JSON.parse(text) as T;
  } catch {
    return { raw: text } as T;
  }
}

export async function apiCall<TResponse>(
  endpoint: ApiEndpointKey | string,
  options: ApiCallOptions = {},
): Promise<TResponse> {
  const url = resolveUrl(endpoint);
  const init: RequestInit = {
    method: options.method ?? "GET",
    headers: {
      "Content-Type": "application/json",
      ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
      ...(options.headers ?? {}),
    },
    signal: options.signal,
  };

  if (options.body !== undefined && init.method !== "GET") {
    init.body = JSON.stringify(options.body);
  }

  const response = await fetch(url, init);
  if (!response.ok) {
    const payload = await parseJson<{ error?: string; message?: string }>(response);
    throw new ApiError(
      payload.error || payload.message || `HTTP ${response.status}`,
      response.status,
      payload,
    );
  }

  return parseJson<TResponse>(response);
}

export async function fetchDashboardHealth(
  token: string,
): Promise<DashboardHealthResponse> {
  return apiCall<DashboardHealthResponse>("health", { token });
}

export async function fetchRagQuery(
  body: RagQueryRequest,
  token: string,
): Promise<RagQueryResponse> {
  return apiCall<RagQueryResponse>("ragQuery", {
    method: "POST",
    body,
    token,
  });
}

export async function fetchDocuments(
  body: DocumentSearchRequest,
  token: string,
): Promise<DocumentSearchResponse> {
  return apiCall<DocumentSearchResponse>("searchDocs", {
    method: "POST",
    body,
    token,
  });
}

export async function fetchAssistant(
  body: AssistantQueryRequest,
  token: string,
): Promise<AssistantQueryResponse> {
  return apiCall<AssistantQueryResponse>("assistantQuery", {
    method: "POST",
    body,
    token,
  });
}

export type { AuditEntry };
