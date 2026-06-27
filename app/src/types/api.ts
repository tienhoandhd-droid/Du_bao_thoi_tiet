export interface DashboardServiceHealth {
  status?: string;
  message?: string;
}

export interface DashboardHealthResponse {
  overall?: string;
  services?: Record<string, DashboardServiceHealth>;
  stats?: Record<string, number>;
  warnings?: string[];
}

export interface RagSource {
  document_code?: string;
  version?: string | number;
  language_code?: string;
  page_number?: string | number;
  section_code?: string;
  section_title?: string;
  source_type?: string;
  relevance_score?: number;
  grounded?: boolean;
  citation_rank?: number;
  claim_text?: string;
  snippet?: string;
}

export interface RagQueryRequest {
  query: string;
  response_language?: string;
  filters?: {
    language_preference?: string | null;
    document_type?: string | null;
  };
}

export interface RagQueryResponse {
  success?: boolean;
  error?: string;
  confidence?: string;
  answer?: string;
  message?: string;
  conflict_warning?: string;
  language_warning?: string;
  disclaimer?: string;
  sources?: RagSource[];
}

export interface DocumentRecord {
  id: string | number;
  document_code?: string;
  document_title?: string;
  document_type?: string;
  language_code?: string;
  version?: string | number;
  status?: string;
  chunk_count?: number;
}

export interface DocumentSearchRequest {
  keyword?: string;
  language_code?: string;
  status?: string;
  limit?: number;
}

export interface DocumentSearchResponse {
  documents?: DocumentRecord[];
}

export interface AuditEntry {
  id?: string | number;
  user_email?: string;
  user_role?: string;
  action_type?: string;
  timestamp?: string;
  input_summary?: string;
  document_code?: string;
  language_code?: string;
}

export interface SecurityCheckItem {
  ok: boolean;
  label: string;
  detail: string;
}

export interface AssistantToolCall {
  name?: string;
  tool_name?: string;
  status?: string;
  arguments?: unknown;
  result?: unknown;
  message?: string;
}

export interface AssistantCitation {
  document_code?: string;
  version?: string | number;
  language_code?: string;
  page_number?: string | number;
  section_code?: string;
  section_title?: string;
  source_type?: string;
  grounded?: boolean;
  citation_rank?: number;
  claim_text?: string;
  snippet?: string;
  relevance_score?: number;
}

export interface AssistantQueryRequest {
  query: string;
  session_id?: string;
  response_language?: string;
  message?: string;
}

export interface AssistantQueryResponse {
  success?: boolean;
  error?: string;
  answer?: string;
  message?: string;
  confidence?: string;
  session_id?: string;
  tool_calls?: AssistantToolCall[];
  tools?: AssistantToolCall[];
  citations?: AssistantCitation[];
  sources?: AssistantCitation[];
  disclaimer?: string;
}
