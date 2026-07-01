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
  source_type?: string;
  language_code?: string;
  version?: string | number;
  status?: string;
  approved_for_ai_use?: boolean;
  file_name?: string;
  page_count?: number;
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

export interface DraftProtocolRequest {
  protocol_type: string;
  equipment_code: string;
  equipment_name?: string;
  template_id?: string | null;
  language_mode?: string;
  special_requirements?: string;
  manufacturer?: string;
  model?: string;
  location?: string;
  intended_use?: string;
}

export interface DraftProtocolResponse {
  success?: boolean;
  error?: string;
  protocol_type?: string;
  equipment_code?: string;
  content?: string;
  disclaimer?: string;
}

export interface CheckProtocolRequest {
  document_text: string;
  protocol_type?: string;
  equipment_code?: string;
  document_language?: string;
}

export interface ProtocolFinding {
  severity?: string;
  layer?: string;
  location?: string;
  finding?: string;
  risk?: string;
  recommendation?: string;
}

export interface CheckProtocolResponse {
  success?: boolean;
  error?: string;
  overall_status?: string;
  overall_score?: number;
  critical_count?: number;
  major_count?: number;
  minor_count?: number;
  findings?: ProtocolFinding[];
  disclaimer?: string;
}

export interface CalculationStep {
  step?: string;
  detail?: string;
}

export interface CalculateReportRequest {
  formula_code: string;
  input_data: Record<string, number | string>;
  job_name?: string;
  acceptance_criteria?: {
    operator: string;
    value: number;
    unit?: string;
    source?: string;
  } | null;
}

export interface CalculateReportResponse {
  success?: boolean;
  error?: string;
  formula?: string;
  formula_code?: string;
  formula_version?: string;
  formula_display?: string;
  reference_source?: string;
  input?: Record<string, unknown>;
  result?: number;
  steps?: CalculationStep[];
  pass_fail?: string;
  criteria_note?: string;
  interpretation?: string;
  disclaimer?: string;
}

export interface CopilotCitation {
  chunk_id: string;
  document_code: string;
  text: string;
}

export interface CopilotQueryRequest {
  query: string;
  equipment_code: string;
  validation_type: string;
  session_id?: string;
}

export interface CopilotQueryResponse {
  answer?: string;
  citations?: CopilotCitation[];
  session_id?: string;
  grounded_pct?: number;
  error?: string;
}

export type WebSearchMode = "general" | "guideline" | "literature" | "forum";

export interface WebSearchRequest {
  query: string;
  search_mode?: WebSearchMode;
  include_domains?: string[];
  max_results?: number;
}

export interface WebSearchResult {
  rank: number;
  title: string;
  url: string;
  content: string;
  relevance_score: number;
  published_date: string | null;
  trust_level: number;
  trust_badge: string;
  source_domain: string;
}

export interface WebSearchResponse {
  results?: WebSearchResult[];
  total?: number;
  query?: string;
  search_mode?: string;
  error?: string;
}
