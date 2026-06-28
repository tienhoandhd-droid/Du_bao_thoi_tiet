import { buildWebhookUrl, getPublicEnv, normalizeBaseUrl } from "@/lib/env";
import type {
  AssistantQueryRequest,
  AssistantQueryResponse,
  AuditEntry,
  CalculateReportRequest,
  CalculateReportResponse,
  CheckProtocolRequest,
  CheckProtocolResponse,
  CopilotQueryRequest,
  CopilotQueryResponse,
  DashboardHealthResponse,
  DocumentSearchRequest,
  DocumentSearchResponse,
  DraftProtocolRequest,
  DraftProtocolResponse,
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
  draftProtocol: buildWebhookUrl("/draft-protocol"),
  checkProtocol: buildWebhookUrl("/check-protocol"),
  calculateReport: buildWebhookUrl("/calculate-report"),
  copilotQuery: buildWebhookUrl("/copilot-query"),
} as const;

export type ApiEndpointKey = keyof typeof apiEndpoints;
export type ApiRequestBody =
  | RagQueryRequest
  | AssistantQueryRequest
  | DocumentSearchRequest
  | DraftProtocolRequest
  | CheckProtocolRequest
  | CalculateReportRequest
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

export async function fetchDraftProtocol(
  body: DraftProtocolRequest,
  token: string,
): Promise<DraftProtocolResponse> {
  return apiCall<DraftProtocolResponse>("draftProtocol", { method: "POST", body, token });
}

export async function fetchCheckProtocol(
  body: CheckProtocolRequest,
  token: string,
): Promise<CheckProtocolResponse> {
  return apiCall<CheckProtocolResponse>("checkProtocol", { method: "POST", body, token });
}

export async function fetchCalculateReport(
  body: CalculateReportRequest,
  token: string,
): Promise<CalculateReportResponse> {
  return apiCall<CalculateReportResponse>("calculateReport", { method: "POST", body, token });
}

// WF-13 reads JWT from ?auth= query param, not Authorization header.
export async function fetchCopilotQuery(
  body: CopilotQueryRequest,
  token: string,
  signal?: AbortSignal,
): Promise<CopilotQueryResponse> {
  const url = `${apiEndpoints.copilotQuery}?auth=${encodeURIComponent(token)}`;
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!response.ok) {
    const payload = await parseJson<{ error?: string; message?: string }>(response);
    throw new ApiError(
      payload.error || payload.message || `HTTP ${response.status}`,
      response.status,
      payload,
    );
  }
  return parseJson<CopilotQueryResponse>(response);
}

export type { AuditEntry };
