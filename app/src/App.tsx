import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
} from "react";
import type { Session } from "@supabase/supabase-js";
import { ApiError, apiEndpoints, fetchDashboardHealth, fetchDocuments, fetchRagQuery } from "@/lib/api";
import { classifyEnvValue, getPublicEnv, maskValue } from "@/lib/env";
import { sb } from "@/lib/supabase";
import { cn } from "@/lib/utils";
import { AssistantPanel } from "@/features/assistant/AssistantPanel";
import { ValidationPage } from "@/features/validation/ValidationPage";
import { FlagQueuePanel } from "@/features/validation/FlagQueuePanel";
import { usePendingFlagCodes } from "@/features/validation/usePendingFlags";
import { WebSearchPanel } from "@/features/search/WebSearchPanel";
import MultimodalSearchPage from "@/features/search/MultimodalSearchPage";
import { TieredAnswer } from "@/features/search/TieredAnswer";
import { ObservabilityPanel, type ObservabilityRow } from "@/features/observability/ObservabilityPanel";
import { EvalPanel } from "@/features/eval/EvalPanel";
import type {
  AuditEntry,
  DashboardHealthResponse,
  DocumentRecord,
  RagQueryResponse,
  SecurityCheckItem,
} from "@/types/api";
import type { EnvCheck } from "@/types/env";

type PageId = "dashboard" | "ai-search" | "documents" | "multimodal" | "web-search" | "audit" | "security" | "validation" | "flags";

const SESSION_TIMEOUT_MS = 8 * 60 * 60 * 1000;

const PAGE_TITLES: Record<PageId, string> = {
  dashboard: "❄ Tổng quan",
  "ai-search": "✦ AI Search / Q&A",
  documents: "❆ Thư viện tài liệu",
  multimodal: "🖼️ Tìm kiếm đa phương thức",
  "web-search": "🔎 Tìm kiếm Web",
  audit: "✧ Audit Trail",
  security: "🔒 Bảo mật",
  validation: "⚗ Công cụ thẩm định",
  flags: "🚩 Hàng đợi cờ AL",
};

const ROLE_LABELS: Record<string, string> = {
  admin: "Quản trị viên",
  qa_manager: "QA Manager",
  validation: "Thẩm định",
  engineering: "Kỹ thuật",
  viewer: "Người xem",
  auditor: "Kiểm toán",
};

const STATUS_LABELS: Record<string, string> = {
  draft: "Bản nháp",
  indexed: "Đã index",
  reviewed: "Đã review",
  approved_for_ai_use: "✓ AI Approved",
  superseded: "Thay thế",
  archived: "Lưu trữ",
};

const SEARCH_LANG_OPTIONS = [
  { value: "any", label: "Tất cả ngôn ngữ" },
  { value: "vi", label: "Tiếng Việt" },
  { value: "en", label: "Tiếng Anh" },
  { value: "vi-en", label: "Song ngữ" },
];

const DOC_TYPE_OPTIONS = [
  { value: "", label: "Tất cả loại" },
  { value: "sop", label: "SOP" },
  { value: "guideline", label: "Guideline" },
  { value: "form", label: "Form" },
  { value: "template", label: "Template" },
  { value: "manual", label: "Manual" },
  { value: "urs", label: "URS" },
];

const DOC_STATUS_OPTIONS = [
  { value: "", label: "Tất cả trạng thái" },
  { value: "draft", label: "Draft" },
  { value: "indexed", label: "Indexed" },
  { value: "reviewed", label: "Reviewed" },
  { value: "approved_for_ai_use", label: "Approved cho AI" },
];

const SQL_INJECTION_PATTERNS = [
  /--|\/\*|\*\//,
  /;\s*(select|insert|update|delete|drop|alter|create|truncate)\b/i,
  /\bunion\s+(all\s+)?select\b/i,
  /\b(insert\s+into|delete\s+from|update\s+\S+\s+set)\b/i,
  /\b(drop|alter|create|truncate)\s+table\b/i,
];

const GOVERNANCE_LAYERS = [
  {
    id: "input",
    title: "Tầng 1 · Input",
    gate: "Query không rỗng, tối đa 500 ký tự và không chứa mẫu SQL injection rõ ràng.",
    failure: "Không đạt: từ chối trước retrieval và không gọi model.",
  },
  {
    id: "retrieval",
    title: "Tầng 2 · Retrieval",
    gate: "Chỉ dùng nguồn approved_for_ai_use=true; mọi tool truy hồi phải đi qua hybrid_search_v3.",
    failure: "Không đủ nguồn: trả trạng thái thiếu căn cứ, không dùng kiến thức ngoài kho đã duyệt.",
  },
  {
    id: "generation",
    title: "Tầng 3 · Generation",
    gate: "Prompt chỉ cho phép trả lời từ nguồn đã truy hồi, không sáng tạo và bắt buộc có disclaimer.",
    failure: "Nguồn không đủ: nói rõ không tìm thấy và chuyển người có chuyên môn kiểm tra.",
  },
  {
    id: "output",
    title: "Tầng 4 · Output",
    gate: "Chỉ phát hành bình thường khi grounded_pct ≥ 0.60 và confidence tối thiểu MEDIUM.",
    failure: "Không đạt: hạ cấp hoặc chặn kết luận, vẫn hiển thị nguồn và disclaimer.",
  },
] as const;

function envStatusLabel(status: EnvCheck["status"]): string {
  switch (status) {
    case "ok":
      return "OK";
    case "missing":
      return "RỖNG";
    case "placeholder":
      return "PLACEHOLDER";
    case "invalid":
      return "SAI";
    default:
      return status;
  }
}

function envStatusClass(status: EnvCheck["status"]): string {
  switch (status) {
    case "ok":
      return "bg-primary/15 text-primary";
    case "missing":
    case "placeholder":
    case "invalid":
      return "bg-destructive/15 text-destructive";
    default:
      return "bg-muted text-muted-foreground";
  }
}

function serviceStatusClass(status?: string): string {
  switch (status) {
    case "healthy":
      return "bg-emerald-500/10 text-emerald-700 border-emerald-500/20";
    case "error":
      return "bg-destructive/10 text-destructive border-destructive/20";
    case "degraded":
      return "bg-amber-500/10 text-amber-700 border-amber-500/20";
    default:
      return "bg-muted text-muted-foreground border-border";
  }
}

function confidenceClass(confidence?: string): string {
  switch ((confidence ?? "").toUpperCase()) {
    case "HIGH":
      return "bg-emerald-500/10 text-emerald-700 border-emerald-500/20";
    case "MEDIUM":
      return "bg-amber-500/10 text-amber-700 border-amber-500/20";
    case "LOW":
      return "bg-rose-500/10 text-rose-700 border-rose-500/20";
    case "BLOCKED":
      return "bg-slate-500/10 text-slate-600 border-slate-500/20";
    default:
      return "bg-muted text-muted-foreground border-border";
  }
}

function sourceTypeClass(sourceType?: string): string {
  switch (sourceType) {
    case "internal_sop":
      return "bg-emerald-500/10 text-emerald-700";
    case "guideline":
      return "bg-primary/10 text-primary";
    case "equipment_doc":
      return "bg-amber-500/10 text-amber-700";
    default:
      return "bg-muted text-muted-foreground";
  }
}

function sourceTypeLabel(sourceType?: string): string {
  switch (sourceType) {
    case "internal_sop":
      return "SOP nội bộ";
    case "guideline":
      return "Tài liệu tham khảo";
    case "equipment_doc":
      return "Tài liệu thiết bị";
    default:
      return sourceType || "Chưa phân loại";
  }
}

function groundedClass(grounded?: boolean): string {
  return grounded
    ? "bg-emerald-500/10 text-emerald-700 border-emerald-500/20"
    : "bg-amber-500/10 text-amber-700 border-amber-500/20";
}

function toNumber(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatDate(value?: string): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("vi-VN");
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "-";
  return String(value);
}

function extractErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return "Đã xảy ra lỗi không xác định";
}

function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}

function roleLabel(role: string): string {
  return ROLE_LABELS[role] || role || "viewer";
}

function normalizeDocuments(rows: DocumentRecord[]): DocumentRecord[] {
  return rows.filter((row) => Boolean(row?.id));
}

function validateGovernedQuery(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return "Câu hỏi không được để trống.";
  if (trimmed.length > 500) return "Câu hỏi không được vượt quá 500 ký tự.";
  if (SQL_INJECTION_PATTERNS.some((pattern) => pattern.test(trimmed))) {
    return "Câu hỏi chứa mẫu lệnh SQL không được phép.";
  }
  return null;
}

export default function App() {
  const env = getPublicEnv();
  const clientReady = sb !== null;

  const checks = useMemo<EnvCheck[]>(
    () => [
      {
        label: "Supabase URL",
        varName: "VITE_SUPABASE_URL",
        display: env.supabaseUrl || "(rỗng)",
        status: classifyEnvValue(env.supabaseUrl, { requireHttp: true }),
      },
      {
        label: "Supabase Anon Key",
        varName: "VITE_SUPABASE_ANON_KEY",
        display: env.supabaseAnonKey ? maskValue(env.supabaseAnonKey) : "(rỗng)",
        status: classifyEnvValue(env.supabaseAnonKey, { requireJwt: true }),
      },
      {
        label: "Webhook Base (n8n)",
        varName: "VITE_WEBHOOK_BASE",
        display: env.webhookBase || "(rỗng)",
        status: classifyEnvValue(env.webhookBase, { requireHttp: true }),
      },
    ],
    [env.supabaseUrl, env.supabaseAnonKey, env.webhookBase],
  );

  const allOk = checks.every((check) => check.status === "ok");

  const [authReady, setAuthReady] = useState(false);
  const [session, setSession] = useState<Session | null>(null);
  const [roles, setRoles] = useState<string[]>([]);
  const [page, setPage] = useState<PageId>("dashboard");
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [loginPending, setLoginPending] = useState(false);

  const [dashboard, setDashboard] = useState<DashboardHealthResponse | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [dashboardError, setDashboardError] = useState("");

  const [query, setQuery] = useState("");
  const [queryLang, setQueryLang] = useState("any");
  const [queryDocType, setQueryDocType] = useState("");
  const [queryResult, setQueryResult] = useState<RagQueryResponse | null>(null);
  const [queryLoading, setQueryLoading] = useState(false);
  const [queryError, setQueryError] = useState("");

  const [docSearch, setDocSearch] = useState("");
  const [docFilterLang, setDocFilterLang] = useState("");
  const [docFilterStatus, setDocFilterStatus] = useState("");
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [documentsError, setDocumentsError] = useState("");

  const [auditEntries, setAuditEntries] = useState<AuditEntry[]>([]);
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditError, setAuditError] = useState("");

  const [securityChecks, setSecurityChecks] = useState<SecurityCheckItem[]>([]);
  const [securityRunning, setSecurityRunning] = useState(false);

  const [observabilityRows, setObservabilityRows] = useState<ObservabilityRow[]>([]);
  const [webSearchInitQuery, setWebSearchInitQuery] = useState("");

  const token = session?.access_token ?? "";

  const resetLocalSession = useCallback(() => {
    setSession(null);
    setRoles([]);
    setPage("dashboard");
  }, []);

  const handleLogout = useCallback(async () => {
    if (sb) {
      try {
        await sb.auth.signOut();
      } catch {
        // Không chặn logout local nếu remote signOut lỗi.
      }
    }
    resetLocalSession();
  }, [resetLocalSession]);

  const loadRoles = useCallback(async (userId: string) => {
    if (!sb) {
      setRoles([]);
      return;
    }

    try {
      const { data, error } = await sb
        .from("user_roles")
        .select("roles(role_name,display_name)")
        .eq("user_id", userId)
        .eq("is_active", true);

      if (error) throw error;

      type UserRoleRow = {
        roles?: {
          role_name?: string | null;
        } | null;
      };

      const values = (data ?? []) as UserRoleRow[];
      setRoles(
        values
          .map((row) => row.roles?.role_name ?? "")
          .filter((value): value is string => Boolean(value)),
      );
    } catch (error) {
      console.warn("[roles]", extractErrorMessage(error));
      setRoles([]);
    }
  }, []);

  const loadDashboard = useCallback(async () => {
    if (!token) return;

    setDashboardLoading(true);
    setDashboardError("");
    try {
      const data = await fetchDashboardHealth(token);
      setDashboard(data);
    } catch (error) {
      if (isUnauthorized(error)) {
        await handleLogout();
        return;
      }
      setDashboardError(extractErrorMessage(error));
    } finally {
      setDashboardLoading(false);
    }
  }, [handleLogout, token]);

  const loadObservability = useCallback(async () => {
    if (!sb) return;
    const since = new Date();
    since.setDate(since.getDate() - 7);
    try {
      const { data } = await sb
        .from("audit_log")
        .select("action_type, timestamp")
        .gte("timestamp", since.toISOString())
        .order("timestamp", { ascending: false })
        .limit(2000);
      setObservabilityRows((data ?? []) as ObservabilityRow[]);
    } catch {
      // Non-blocking — dashboard still shows without observability stats
    }
  }, []);

  const loadDocuments = useCallback(async () => {
    if (!token) return;

    setDocumentsLoading(true);
    setDocumentsError("");
    try {
      const data = await fetchDocuments(
        {
          keyword: docSearch.trim() || undefined,
          language_code: docFilterLang || undefined,
          status: docFilterStatus || undefined,
          limit: 50,
        },
        token,
      );
      setDocuments(normalizeDocuments((data.documents ?? []) as DocumentRecord[]));
    } catch (error) {
      if (isUnauthorized(error)) {
        await handleLogout();
        return;
      }
      setDocumentsError(extractErrorMessage(error));
    } finally {
      setDocumentsLoading(false);
    }
  }, [docFilterLang, docFilterStatus, docSearch, handleLogout, token]);

  const loadAudit = useCallback(async () => {
    if (!sb) return;

    setAuditLoading(true);
    setAuditError("");
    try {
      const { data, error } = await sb
        .from("audit_log")
        .select("id,user_email,user_role,action_type,\"timestamp\",input_summary,document_code,language_code")
        .order("timestamp", { ascending: false })
        .limit(30);

      if (error) throw error;
      setAuditEntries((data ?? []) as AuditEntry[]);
    } catch (error) {
      setAuditError(extractErrorMessage(error));
    } finally {
      setAuditLoading(false);
    }
  }, []);

  const runSecurityCheck = useCallback(async () => {
    if (!sb) return;

    setSecurityRunning(true);
    const results: SecurityCheckItem[] = [];
    const push = (ok: boolean, label: string, detail: string) => {
      results.push({ ok, label, detail });
    };

    const envSource = JSON.stringify(import.meta.env);
    push(
      !envSource.includes("service_role"),
      "Frontend không chứa service_role key",
      envSource.includes("service_role")
        ? "NGUY HIỂM: Tìm thấy service_role trong bundle/env."
        : "Chỉ có anon key hoặc biến công khai.",
    );

    try {
      const { error } = await sb.from("roles").select("id").limit(1);
      push(!error, "Supabase RLS hoạt động", error ? error.message : "Query qua RLS thành công");
    } catch (error) {
      push(false, "Supabase RLS hoạt động", extractErrorMessage(error));
    }

    try {
      const health = await fetchDashboardHealth(token);
      push(
        (health.overall ?? "") !== "error",
        "n8n Webhooks hoạt động",
        `Overall: ${health.overall ?? "unknown"}`,
      );
    } catch (error) {
      push(false, "n8n Webhooks hoạt động", extractErrorMessage(error));
    }

    push(
      Boolean(token),
      "JWT Token hợp lệ",
      token ? `Token có ${token.length} ký tự` : "Không có token!",
    );

    try {
      const { error } = await sb.from("audit_log").select("id").limit(1);
      push(!error, "Audit log truy xuất được", error ? error.message : "Append-only log sẵn sàng");
    } catch (error) {
      push(false, "Audit log truy xuất được", extractErrorMessage(error));
    }

    push(
      window.location.protocol === "https:",
      "Kết nối HTTPS",
      window.location.protocol === "https:"
        ? "Mã hóa đường truyền"
        : "CẢNH BÁO: đang dùng HTTP.",
    );

    setSecurityChecks(results);
    setSecurityRunning(false);
  }, [token]);

  const submitQuery = useCallback(
    async (event?: FormEvent<HTMLFormElement>) => {
      event?.preventDefault();
      const trimmed = query.trim();
      const validationError = validateGovernedQuery(trimmed);
      if (validationError) {
        setQueryResult(null);
        setQueryError(validationError);
        return;
      }

      setQueryLoading(true);
      setQueryError("");
      setQueryResult(null);

      try {
        const data = await fetchRagQuery(
          {
            query: trimmed,
            response_language: "vi",
            filters: {
              language_preference: queryLang,
              document_type: queryDocType || null,
            },
          },
          token,
        );
        setQueryResult(data);
      } catch (error) {
        if (isUnauthorized(error)) {
          await handleLogout();
          return;
        }
        setQueryError(extractErrorMessage(error));
      } finally {
        setQueryLoading(false);
      }
    },
    [handleLogout, query, queryDocType, queryLang, token],
  );

  const submitDocuments = useCallback(
    async (event?: FormEvent<HTMLFormElement>) => {
      event?.preventDefault();
      await loadDocuments();
    },
    [loadDocuments],
  );

  const handleLogin = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();

      const email = loginEmail.trim();
      const password = loginPassword;

      if (!email || !password) {
        setLoginError("Vui lòng nhập email và mật khẩu");
        return;
      }

      if (!sb) {
        setLoginError("Hệ thống chưa khởi tạo. Kiểm tra cấu hình VITE_*.");
        return;
      }

      setLoginPending(true);
      setLoginError("");

      try {
        const { data, error } = await sb.auth.signInWithPassword({ email, password });
        if (error) throw error;

        if (data.session) {
          setSession(data.session);
          await loadRoles(data.session.user.id);
          setAuthReady(true);
          setLoginPassword("");
        }
      } catch (error) {
        const message = extractErrorMessage(error);
        setLoginError(
          message === "Invalid login credentials"
            ? "Sai email hoặc mật khẩu"
            : `Lỗi: ${message}`,
        );
      } finally {
        setLoginPending(false);
      }
    },
    [loadRoles, loginEmail, loginPassword],
  );

  useEffect(() => {
    let active = true;

    async function boot() {
      if (!sb) {
        setAuthReady(true);
        return;
      }

      const {
        data: { session: initialSession },
      } = await sb.auth.getSession();

      if (!active) return;

      if (initialSession) {
        setSession(initialSession);
        await loadRoles(initialSession.user.id);
      }

      setAuthReady(true);
    }

    void boot();

    const { data } = sb
      ? sb.auth.onAuthStateChange((event, nextSession) => {
          if (event === "SIGNED_OUT" || !nextSession) {
            resetLocalSession();
            return;
          }

          setSession(nextSession);
          void loadRoles(nextSession.user.id);
        })
      : { data: { subscription: { unsubscribe() {} } } };

    return () => {
      active = false;
      data.subscription.unsubscribe();
    };
  }, [loadRoles, resetLocalSession]);

  useEffect(() => {
    if (!session) return undefined;

    const timer = window.setTimeout(() => {
      void handleLogout();
    }, SESSION_TIMEOUT_MS);

    return () => window.clearTimeout(timer);
  }, [handleLogout, page, session]);

  useEffect(() => {
    if (!session) return;

    if (page === "dashboard") {
      void loadDashboard();
      void loadObservability();
    }
    if (page === "documents") void loadDocuments();
    if (page === "audit") void loadAudit();
  }, [loadAudit, loadDashboard, loadDocuments, loadObservability, page, session]);

  const currentRoleLabel = roleLabel(roles[0] || "viewer");

  if (!authReady) {
    return (
      <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(58,134,199,0.14),_transparent_38%),linear-gradient(180deg,_#f8fafd_0%,_#eef5fc_100%)] px-6 py-10 text-foreground">
        <div className="mx-auto flex min-h-[70vh] max-w-4xl items-center justify-center">
          <p className="text-sm text-muted-foreground">Đang khởi tạo phiên đăng nhập...</p>
        </div>
      </main>
    );
  }

  if (!session) {
    return (
      <LoginScreen
        checks={checks}
        allOk={allOk}
        clientReady={clientReady}
        loginEmail={loginEmail}
        loginError={loginError}
        loginPassword={loginPassword}
        loginPending={loginPending}
        onEmailChange={setLoginEmail}
        onPasswordChange={setLoginPassword}
        onSubmit={handleLogin}
      />
    );
  }

  return (
    <Shell
      currentRoleLabel={currentRoleLabel}
      page={page}
      pageTitle={PAGE_TITLES[page]}
      session={session}
      onLogout={handleLogout}
      onPageChange={setPage}
    >
      {page === "dashboard" ? (
        <DashboardPage
          data={dashboard}
          error={dashboardError}
          loading={dashboardLoading}
          observabilityRows={observabilityRows}
        />
      ) : null}

      {page === "ai-search" ? (
        <AiSearchPage
          docType={queryDocType}
          loading={queryLoading}
          lang={queryLang}
          onDocTypeChange={setQueryDocType}
          onLangChange={setQueryLang}
          onQueryChange={setQuery}
          onSubmit={submitQuery}
          query={query}
          result={queryResult}
          error={queryError}
          token={token}
          onWebSearch={(q) => { setWebSearchInitQuery(q); setPage("web-search"); }}
        />
      ) : null}

      {page === "documents" ? (
        <DocumentsPage
          docFilterLang={docFilterLang}
          docFilterStatus={docFilterStatus}
          docSearch={docSearch}
          error={documentsError}
          loading={documentsLoading}
          onDocFilterLangChange={setDocFilterLang}
          onDocFilterStatusChange={setDocFilterStatus}
          onDocSearchChange={setDocSearch}
          onSubmit={submitDocuments}
          documents={documents}
          roles={roles}
          onReload={() => void loadDocuments()}
        />
      ) : null}

      {page === "multimodal" ? <MultimodalSearchPage /> : null}

      {page === "web-search" ? (
        <WebSearchPanel
          token={token}
          initQuery={webSearchInitQuery}
          onUnauthorized={() => void handleLogout()}
        />
      ) : null}

      {page === "audit" ? (
        <AuditPage error={auditError} loading={auditLoading} entries={auditEntries} />
      ) : null}

      {page === "security" ? (
        <>
          <SecurityPage
            checks={securityChecks}
            loading={securityRunning}
            onRun={runSecurityCheck}
          />
          <EvalPanel />
        </>
      ) : null}

      {page === "validation" && sb ? (
        <ValidationPage sb={sb} token={token} onUnauthorized={() => void handleLogout()} />
      ) : null}
      {page === "flags" ? <FlagQueuePanel /> : null}
    </Shell>
  );
}

function LoginScreen({
  checks,
  allOk,
  clientReady,
  loginEmail,
  loginError,
  loginPassword,
  loginPending,
  onEmailChange,
  onPasswordChange,
  onSubmit,
}: {
  checks: EnvCheck[];
  allOk: boolean;
  clientReady: boolean;
  loginEmail: string;
  loginError: string;
  loginPassword: string;
  loginPending: boolean;
  onEmailChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <main className="min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top,_rgba(58,134,199,0.18),_transparent_32%),linear-gradient(160deg,_#0d1b2a_0%,_#1b3a4b_28%,_#3a86c7_62%,_#eef5fc_100%)] px-4 py-6 text-foreground md:px-6 md:py-10">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <Snowfield />
      </div>

      <div className="relative mx-auto grid min-h-[calc(100vh-3rem)] max-w-6xl items-center gap-6 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
        <section className="rounded-3xl border border-white/20 bg-white/75 p-6 shadow-[0_24px_80px_rgba(13,27,42,0.22)] backdrop-blur-xl md:p-8">
          <div className="mb-6 space-y-3">
            <div className="inline-flex items-center gap-2 rounded-full border border-primary/15 bg-primary/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.22em] text-primary">
              CRAVE · React parity
            </div>
            <h1 className="text-3xl font-semibold tracking-tight text-slate-900 md:text-4xl">
              GMP Validation Intelligence
            </h1>
            <p className="max-w-xl text-sm leading-6 text-slate-600">
              Đăng nhập Supabase Auth để vào dashboard. PHA 1B giữ đúng hành vi cũ
              của 5 trang, nhưng toàn bộ render đi qua JSX để vá F4.
            </p>
          </div>

          <form className="space-y-4" onSubmit={onSubmit}>
            <Field
              label="Email"
              type="email"
              value={loginEmail}
              onChange={onEmailChange}
              placeholder="email@company.com"
              autoComplete="email"
            />
            <Field
              label="Mật khẩu"
              type="password"
              value={loginPassword}
              onChange={onPasswordChange}
              placeholder="••••••••"
              autoComplete="current-password"
            />

            {loginError ? (
              <Alert tone="danger">{loginError}</Alert>
            ) : null}

            <Button className="w-full" disabled={!clientReady || loginPending} type="submit">
              {loginPending ? "Đang đăng nhập..." : "❄ Đăng nhập"}
            </Button>

            {!clientReady ? (
              <p className="text-xs text-rose-700">
                Client Supabase chưa khởi tạo. Kiểm tra `VITE_SUPABASE_URL` và
                `VITE_SUPABASE_ANON_KEY`.
              </p>
            ) : null}
          </form>
        </section>

        <section className="space-y-4">
          <Panel title="Kiểm tra cấu hình">
            <div className="space-y-3">
              {checks.map((check) => (
                <div
                  key={check.varName}
                  className="flex items-start justify-between gap-3 rounded-2xl border border-border bg-background/80 px-4 py-3"
                >
                  <div className="min-w-0 space-y-1">
                    <p className="text-sm font-medium">{check.label}</p>
                    <p className="break-all font-mono text-xs text-muted-foreground">
                      {check.varName} = {check.display}
                    </p>
                  </div>
                  <Badge className={envStatusClass(check.status)}>
                    {envStatusLabel(check.status)}
                  </Badge>
                </div>
              ))}
            </div>
          </Panel>

          <Panel title="API endpoints">
            <div className="space-y-2">
              {Object.entries(apiEndpoints).map(([key, value]) => (
                <div
                  key={key}
                  className="rounded-2xl border border-border bg-background/80 px-4 py-3"
                >
                  <p className="text-sm font-medium">{key}</p>
                  <p className="break-all font-mono text-xs text-muted-foreground">
                    {value}
                  </p>
                </div>
              ))}
            </div>
          </Panel>

          <p
            className={cn(
              "rounded-2xl px-4 py-3 text-sm font-medium",
              allOk
                ? "bg-emerald-500/10 text-emerald-800"
                : "bg-amber-500/10 text-amber-800",
            )}
          >
            {allOk
              ? "Đủ biến môi trường công khai. Sẵn sàng vào shell parity."
              : "Còn biến thiếu hoặc placeholder. Kiểm tra GitHub Repository Variables."}
          </p>
        </section>
      </div>
    </main>
  );
}

function Shell({
  currentRoleLabel,
  page,
  pageTitle,
  session,
  onLogout,
  onPageChange,
  children,
}: {
  currentRoleLabel: string;
  page: PageId;
  pageTitle: string;
  session: Session;
  onLogout: () => Promise<void>;
  onPageChange: (page: PageId) => void;
  children: ReactNode;
}) {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(58,134,199,0.08),_transparent_28%),linear-gradient(180deg,_#f8fafd_0%,_#eef5fc_100%)] text-foreground">
      <div className="flex min-h-screen flex-col md:flex-row">
        <aside className="hidden w-[260px] shrink-0 border-r border-border/60 bg-slate-950 text-white shadow-[4px_0_24px_rgba(13,27,42,0.16)] md:fixed md:inset-y-0 md:flex md:flex-col">
          <div className="border-b border-white/10 px-6 py-5">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-white/50">
              CRAVE
            </p>
            <h2 className="mt-1 text-lg font-semibold">GMP Validation</h2>
            <p className="text-xs text-white/55">Intelligence Dashboard</p>
          </div>

          <nav className="flex-1 space-y-1 px-3 py-4">
            <NavItem active={page === "dashboard"} onClick={() => onPageChange("dashboard")}>
              ❄ Tổng quan
            </NavItem>
            <NavItem active={page === "ai-search"} onClick={() => onPageChange("ai-search")}>
              ✦ AI Search / Q&A
            </NavItem>
            <NavItem active={page === "documents"} onClick={() => onPageChange("documents")}>
              ❆ Thư viện tài liệu
            </NavItem>
            <NavItem active={page === "multimodal"} onClick={() => onPageChange("multimodal")}>
              🖼️ Đa phương thức
            </NavItem>
            <NavItem active={page === "web-search"} onClick={() => onPageChange("web-search")}>
              🔎 Tìm kiếm Web
            </NavItem>
            <div className="my-2 border-t border-white/10" />
            <NavItem active={page === "audit"} onClick={() => onPageChange("audit")}>
              ✧ Audit Trail
            </NavItem>
            <NavItem active={page === "security"} onClick={() => onPageChange("security")}>
              🔒 Bảo mật
            </NavItem>
            <NavItem active={page === "validation"} onClick={() => onPageChange("validation")}>
              ⚗ Công cụ thẩm định
            </NavItem>
            <NavItem active={page === "flags"} onClick={() => onPageChange("flags")}>
              🚩 Hàng đợi cờ AL
            </NavItem>
          </nav>
        </aside>

        <div className="flex min-h-screen flex-1 flex-col md:pl-[260px]">
          <header className="sticky top-0 z-20 border-b border-border/60 bg-white/75 backdrop-blur-xl">
            <div className="flex items-center justify-between gap-4 px-4 py-3 md:px-7">
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                  {pageTitle}
                </p>
                <h1 className="text-lg font-semibold text-slate-900 md:text-xl">
                  {pageTitle}
                </h1>
              </div>

              <div className="flex items-center gap-3 text-sm text-slate-600">
                <div className="hidden flex-col items-end sm:flex">
                  <span className="font-medium text-slate-900">{session.user.email}</span>
                  <span className="text-xs text-muted-foreground">{currentRoleLabel}</span>
                </div>
                <Button variant="secondary" onClick={() => void onLogout()}>
                  Đăng xuất
                </Button>
              </div>
            </div>

            <div className="border-t border-border/60 px-4 py-3 md:hidden">
              <div className="flex gap-2 overflow-x-auto pb-1">
                <MobileNavItem active={page === "dashboard"} onClick={() => onPageChange("dashboard")}>
                  Tổng quan
                </MobileNavItem>
                <MobileNavItem active={page === "ai-search"} onClick={() => onPageChange("ai-search")}>
                  AI Search
                </MobileNavItem>
                <MobileNavItem active={page === "documents"} onClick={() => onPageChange("documents")}>
                  Tài liệu
                </MobileNavItem>
                <MobileNavItem active={page === "multimodal"} onClick={() => onPageChange("multimodal")}>
                  Đa phương thức
                </MobileNavItem>
                <MobileNavItem active={page === "web-search"} onClick={() => onPageChange("web-search")}>
                  Tìm kiếm Web
                </MobileNavItem>
                <MobileNavItem active={page === "audit"} onClick={() => onPageChange("audit")}>
                  Audit
                </MobileNavItem>
                <MobileNavItem active={page === "security"} onClick={() => onPageChange("security")}>
                  Bảo mật
                </MobileNavItem>
                <MobileNavItem active={page === "validation"} onClick={() => onPageChange("validation")}>
                  Thẩm định
                </MobileNavItem>
                <MobileNavItem active={page === "flags"} onClick={() => onPageChange("flags")}>
                  Cờ AL
                </MobileNavItem>
              </div>
            </div>
          </header>

          <main className="flex-1 px-4 py-5 md:px-7 md:py-6">
            <div className="space-y-5">{children}</div>
          </main>
        </div>
      </div>
    </main>
  );
}

function CragBadge({
  sources,
  query,
  onWebSearch,
}: {
  sources?: RagQueryResponse["sources"];
  query: string;
  onWebSearch: (q: string) => void;
}) {
  if (!sources?.length) return null;

  const avg = sources.reduce((s, r) => s + (r.relevance_score ?? 0), 0) / sources.length;
  const level = avg >= 0.65 ? "high" : avg >= 0.42 ? "medium" : "low";

  if (level === "high") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-700">
        🟢 CRAG: Nguồn SOP khớp tốt ({avg.toFixed(2)})
      </span>
    );
  }
  if (level === "medium") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2.5 py-0.5 text-[11px] font-semibold text-amber-700">
        🟡 CRAG: Nguồn khớp một phần ({avg.toFixed(2)})
      </span>
    );
  }
  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      <span className="inline-flex items-center gap-1 rounded-full border border-rose-200 bg-rose-50 px-2.5 py-0.5 text-[11px] font-semibold text-rose-700">
        🔴 CRAG: Ít nguồn SOP phù hợp ({avg.toFixed(2)})
      </span>
      <button
        type="button"
        onClick={() => onWebSearch(query)}
        className="inline-flex items-center gap-1 rounded-full border border-primary/30 bg-primary/8 px-2.5 py-0.5 text-[11px] font-semibold text-primary transition-colors hover:bg-primary/15"
      >
        🔎 Thử tìm kiếm web →
      </button>
    </span>
  );
}

function DashboardPage({
  data,
  loading,
  error,
  observabilityRows,
}: {
  data: DashboardHealthResponse | null;
  loading: boolean;
  error: string;
  observabilityRows: ObservabilityRow[];
}) {
  const stats = data?.stats ?? {};
  const warnings = data?.warnings ?? [];
  const services = data?.services ?? {};

  const statCards = [
    { key: "total_documents", label: "Tổng tài liệu" },
    { key: "sop_count", label: "SOP" },
    { key: "guideline_count", label: "Guideline" },
    { key: "form_count", label: "Form / Template" },
    { key: "docs_vi", label: "Tiếng Việt" },
    { key: "docs_en", label: "Tiếng Anh" },
    { key: "docs_bilingual", label: "Song ngữ" },
    { key: "docs_approved", label: "Approved cho AI", tone: "success" as const },
    { key: "docs_pending_review", label: "Chờ review", tone: "warning" as const },
    {
      key: "ai_translations_pending",
      label: "Bản dịch AI chưa duyệt",
      tone: stats.ai_translations_pending ? ("warning" as const) : undefined,
    },
    { key: "total_ai_queries", label: "Tổng AI queries" },
    { key: "total_users", label: "Người dùng" },
    {
      key: "failed_jobs",
      label: "Job lỗi",
      tone: stats.failed_jobs ? ("danger" as const) : undefined,
    },
    {
      key: "unresolved_security_events",
      label: "Sự kiện bảo mật",
      tone: stats.unresolved_security_events ? ("danger" as const) : undefined,
    },
  ];

  return (
    <>
      <Panel title="Trạng thái hệ thống">
        {loading ? (
          <StateBlock>Đang kiểm tra hệ thống...</StateBlock>
        ) : error ? (
          <Alert tone="danger">Lỗi: {error}</Alert>
        ) : (
          <div className="flex flex-wrap gap-2">
            {Object.entries(services).length ? (
              Object.entries(services).map(([name, service]) => (
                <Pill
                  key={name}
                  className={serviceStatusClass(service.status)}
                >
                  <span className="inline-block h-2 w-2 rounded-full bg-current" />
                  {name}: {service.message || "unknown"}
                </Pill>
              ))
            ) : (
              <StateBlock>Chưa có dữ liệu health.</StateBlock>
            )}
          </div>
        )}
      </Panel>

      <Panel title="Tổng quan số liệu">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {statCards.map((stat) => (
            <StatCard
              key={stat.key}
              label={stat.label}
              tone={stat.tone}
              value={toNumber(stats[stat.key])}
            />
          ))}
        </div>
      </Panel>

      <Panel title="Cảnh báo hệ thống">
        {warnings.length ? (
          <div className="space-y-2">
            {warnings.map((warning, index) => (
              <Alert key={`${warning}-${index}`} tone="warning">
                ⚠ {warning}
              </Alert>
            ))}
          </div>
        ) : (
          <StateBlock>✓ Không có cảnh báo — hệ thống hoạt động bình thường</StateBlock>
        )}
      </Panel>

      <ObservabilityPanel rows={observabilityRows} />
    </>
  );
}

function AiSearchPage({
  query,
  lang,
  docType,
  loading,
  error,
  result,
  onQueryChange,
  onLangChange,
  onDocTypeChange,
  onSubmit,
  token,
  onWebSearch,
}: {
  query: string;
  lang: string;
  docType: string;
  loading: boolean;
  error: string;
  result: RagQueryResponse | null;
  onQueryChange: (value: string) => void;
  onLangChange: (value: string) => void;
  onDocTypeChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  token: string;
  onWebSearch: (query: string) => void;
}) {
  const flaggedCodes = usePendingFlagCodes();
  return (
    <>
      <Panel title="Hỏi AI về SOP, Guideline, Đề cương">
        <form className="space-y-4" onSubmit={onSubmit}>
          <div className="flex flex-col gap-3 md:flex-row">
            <Input
              className="min-h-12 flex-1"
              maxLength={500}
              placeholder="Ví dụ: Điều kiện tiên quyết IQ nằm ở SOP nào?"
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
            />
            <Button disabled={loading} type="submit">
              {loading ? "Đang tìm..." : "Tìm kiếm"}
            </Button>
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <Select value={lang} onChange={(event) => onLangChange(event.target.value)}>
              {SEARCH_LANG_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
            <Select
              value={docType}
              onChange={(event) => onDocTypeChange(event.target.value)}
            >
              {DOC_TYPE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </div>
        </form>
      </Panel>

      {error ? <Alert tone="danger">Lỗi: {error}</Alert> : null}

      {loading ? <StateBlock>Đang phân tích câu hỏi và tìm kiếm nguồn...</StateBlock> : null}

      {result ? (
        <Panel title="Kết quả trả lời">
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm text-muted-foreground">Mức tin cậy:</span>
              <Badge className={confidenceClass(result.confidence)}>
                {result.confidence || "UNKNOWN"}
              </Badge>
              <CragBadge sources={result.sources} query={query} onWebSearch={onWebSearch} />
            </div>

            {result.conflict_warning ? (
              <Alert tone="warning">⚠ {result.conflict_warning}</Alert>
            ) : null}
            {result.language_warning ? (
              <Alert tone="warning">🌐 {result.language_warning}</Alert>
            ) : null}

            <TieredAnswer text={result.answer || result.message || "Không có nội dung trả lời."} />

            {result.sources?.length ? (
              <details open className="overflow-hidden rounded-2xl border border-border bg-white shadow-sm">
                <summary className="cursor-pointer border-b border-border px-5 py-4 text-sm font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                  Nguồn tham chiếu ({result.sources.length})
                </summary>
                <div className="overflow-x-auto">
                  <table className="min-w-full border-collapse text-sm">
                    <thead className="bg-slate-50 text-left text-[11px] uppercase tracking-[0.14em] text-slate-500">
                      <tr>
                        <Th>#</Th>
                        <Th>Mã tài liệu</Th>
                        <Th>Phiên bản</Th>
                        <Th>Ngôn ngữ</Th>
                        <Th>Trang</Th>
                        <Th>Mục</Th>
                        <Th>Loại</Th>
                        <Th>Trạng thái</Th>
                        <Th>Điểm</Th>
                        <Th>Claim</Th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.sources.map((source, index) => (
                        <tr key={`${source.document_code ?? "source"}-${index}`} className="border-t border-border/60">
                          <Td>{index + 1}</Td>
                          <Td className="font-semibold">
                            {formatValue(source.document_code)}
                            {source.document_code && flaggedCodes.has(source.document_code) ? (
                              <span
                                title="Tài liệu có điểm dữ liệu chưa khớp, đang chờ QA duyệt chính thức"
                                className="ml-1 rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-800"
                              >
                                🚩 chờ QA
                              </span>
                            ) : null}
                          </Td>
                          <Td>{formatValue(source.version ?? "-")}</Td>
                          <Td>
                            <Badge className="bg-slate-100 text-slate-700">
                              {formatValue(source.language_code ?? "-")}
                            </Badge>
                          </Td>
                          <Td>{formatValue(source.page_number ?? "-")}</Td>
                          <Td>
                            <div className="max-w-[220px]">
                              <p className="truncate">
                                {formatValue(source.section_code)} {formatValue(source.section_title)}
                              </p>
                            </div>
                          </Td>
                          <Td>
                            <Badge className={sourceTypeClass(source.source_type)}>
                              {formatValue(source.source_type ?? "-")}
                            </Badge>
                          </Td>
                          <Td>
                            <Badge className={groundedClass(source.grounded)}>
                              grounded={source.grounded ? "true" : "false"}
                            </Badge>
                          </Td>
                          <Td>{(source.relevance_score ?? 0).toFixed(2)}</Td>
                          <Td>
                            <div className="max-w-[280px] whitespace-normal text-slate-600">
                              {formatValue(source.claim_text || source.snippet)}
                            </div>
                          </Td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>
            ) : null}

            <Alert tone="info">
              ⚕ {result.disclaimer || "Nội dung do AI tạo (DRAFT), cần người có chuyên môn xem xét trước khi dùng cho hồ sơ GMP chính thức."}
            </Alert>
          </div>
        </Panel>
      ) : null}

      <AssistantPanel token={token} />
    </>
  );
}

function DocumentsPage({
  docSearch,
  docFilterLang,
  docFilterStatus,
  documents,
  loading,
  error,
  onDocSearchChange,
  onDocFilterLangChange,
  onDocFilterStatusChange,
  onSubmit,
  roles,
  onReload,
}: {
  docSearch: string;
  docFilterLang: string;
  docFilterStatus: string;
  documents: DocumentRecord[];
  loading: boolean;
  error: string;
  onDocSearchChange: (value: string) => void;
  onDocFilterLangChange: (value: string) => void;
  onDocFilterStatusChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  roles: string[];
  onReload: () => void;
}) {
  const canManage = roles.some((r) => r === "admin" || r === "qa_manager");
  const [busyId, setBusyId] = useState<string | null>(null);
  async function toggleLifecycle(doc: DocumentRecord) {
    if (!sb) return;
    const status = String(doc.status);
    const pending = status !== "approved_for_ai_use" && status !== "archived";
    setBusyId(String(doc.id));
    try {
      const { error: err } =
        status === "archived"
          ? await sb.rpc("reactivate_document", { p_doc_id: String(doc.id) })
          : pending
            ? await sb.rpc("approve_document", { p_doc_id: String(doc.id) })
            : await sb.rpc("retire_document", { p_doc_id: String(doc.id), p_reason: "Hết hạn/ngừng dùng" });
      if (err) throw err;
      onReload();
    } catch (e) {
      alert("Lỗi vòng đời: " + (e instanceof Error ? e.message : "không đổi được (cần quyền admin/qa_manager)"));
    } finally {
      setBusyId(null);
    }
  }
  return (
    <>
      <Panel title="Thư viện tài liệu">
        <form className="space-y-4" onSubmit={onSubmit}>
          <div className="flex flex-col gap-3 lg:flex-row">
            <Input
              className="min-h-12 flex-1"
              placeholder="Tìm theo mã hoặc tên..."
              value={docSearch}
              onChange={(event) => onDocSearchChange(event.target.value)}
            />
            <Button disabled={loading} type="submit">
              {loading ? "Đang tìm..." : "Tìm"}
            </Button>
          </div>

          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            <Select
              value={docFilterLang}
              onChange={(event) => onDocFilterLangChange(event.target.value)}
            >
              {SEARCH_LANG_OPTIONS.map((option) => (
                <option key={option.value} value={option.value === "any" ? "" : option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
            <Select
              value={docFilterStatus}
              onChange={(event) => onDocFilterStatusChange(event.target.value)}
            >
              {DOC_STATUS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </div>
        </form>
      </Panel>

      {error ? <Alert tone="danger">Lỗi: {error}</Alert> : null}
      {loading ? <StateBlock>Đang tải...</StateBlock> : null}

      <Panel title="Danh sách tài liệu">
        <p className="mb-4 text-sm text-muted-foreground">
          Tài liệu tham khảo từ Drive được hiển thị tách biệt với SOP nội bộ. Mục
          “Chờ review” không được dùng làm căn cứ quyết định GMP hoặc nguồn cho AI
          cho tới khi đủ lineage, review và index.
        </p>
        {documents.length ? (
          <div className="overflow-x-auto">
            <table className="min-w-full border-collapse text-sm">
              <thead className="bg-slate-50 text-left text-[11px] uppercase tracking-[0.14em] text-slate-500">
                <tr>
                  <Th>Mã</Th>
                  <Th>Tên</Th>
                  <Th>Loại</Th>
                  <Th>Nguồn</Th>
                  <Th>Ngôn ngữ</Th>
                  <Th>Phiên bản</Th>
                  <Th>Trạng thái</Th>
                  <Th>AI</Th>
                  <Th>Chunks</Th>
                  <Th>Vòng đời</Th>
                </tr>
              </thead>
              <tbody>
                {documents.map((document) => (
                  <tr key={String(document.id)} className="border-t border-border/60">
                    <Td className="font-semibold">
                      {formatValue(document.document_code)}
                    </Td>
                    <Td>{formatValue(document.document_title)}</Td>
                    <Td>{formatValue(document.document_type)}</Td>
                    <Td>
                      <Badge className={sourceTypeClass(document.source_type)}>
                        {sourceTypeLabel(document.source_type)}
                      </Badge>
                    </Td>
                    <Td>
                      <Badge className="bg-slate-100 text-slate-700">
                        {formatValue(document.language_code)}
                      </Badge>
                    </Td>
                    <Td>v{formatValue(document.version)}</Td>
                    <Td>
                      <Badge className={documentStatusClass(String(document.status || ""))}>
                        {STATUS_LABELS[String(document.status || "")] || String(document.status || "-")}
                      </Badge>
                    </Td>
                    <Td>
                      <Badge
                        className={
                          document.approved_for_ai_use
                            ? "bg-emerald-500/10 text-emerald-700"
                            : "bg-amber-500/10 text-amber-700"
                        }
                      >
                        {document.approved_for_ai_use ? "Sẵn sàng AI" : "Chờ review"}
                      </Badge>
                    </Td>
                    <Td>{document.chunk_count ?? 0}</Td>
                    <Td>
                      {canManage ? (
                        <button
                          type="button"
                          disabled={busyId === String(document.id)}
                          onClick={() => toggleLifecycle(document)}
                          className={cn(
                            "rounded-md px-2 py-1 text-[11px] font-semibold text-white disabled:opacity-50",
                            String(document.status) === "archived"
                              ? "bg-emerald-600"
                              : String(document.status) === "approved_for_ai_use"
                                ? "bg-rose-600"
                                : "bg-indigo-600",
                          )}
                        >
                          {String(document.status) === "archived"
                            ? "Kích hoạt lại"
                            : String(document.status) === "approved_for_ai_use"
                              ? "Ngừng dùng"
                              : "Duyệt cho AI"}
                        </button>
                      ) : (
                        <span className="text-[11px] text-slate-400">—</span>
                      )}
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <StateBlock>❄ Không tìm thấy tài liệu nào.</StateBlock>
        )}
      </Panel>
    </>
  );
}

function AuditPage({
  entries,
  loading,
  error,
}: {
  entries: AuditEntry[];
  loading: boolean;
  error: string;
}) {
  const actionMap: Record<string, string> = {
    document_upload: "Upload tài liệu",
    document_index: "Index tài liệu",
    document_review: "Review tài liệu",
    document_approve: "Duyệt tài liệu",
    ai_query: "Hỏi AI",
    ai_draft_protocol: "Viết đề cương",
    ai_check_protocol: "Check đề cương",
    user_login: "Đăng nhập",
    config_change: "Thay đổi cấu hình",
    security_event: "Sự kiện bảo mật",
  };

  return (
    <Panel title="Nhật ký hoạt động (Audit Trail — ALCOA+)">
      {loading ? <StateBlock>Đang tải nhật ký...</StateBlock> : null}
      {error ? <Alert tone="danger">Lỗi: {error}</Alert> : null}

      {!loading && !error && entries.length === 0 ? (
        <StateBlock>Chưa có nhật ký nào.</StateBlock>
      ) : null}

      {entries.length ? (
        <div className="overflow-x-auto">
          <table className="min-w-full border-collapse text-sm">
            <thead className="bg-slate-50 text-left text-[11px] uppercase tracking-[0.14em] text-slate-500">
              <tr>
                <Th>Thời gian</Th>
                <Th>Người dùng</Th>
                <Th>Vai trò</Th>
                <Th>Hành động</Th>
                <Th>Tóm tắt</Th>
                <Th>Tài liệu</Th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry, index) => (
                <tr key={`${entry.id ?? "audit"}-${index}`} className="border-t border-border/60">
                  <Td className="whitespace-nowrap text-xs text-slate-600">
                    {formatDate(entry.timestamp)}
                  </Td>
                  <Td>{formatValue(entry.user_email)}</Td>
                  <Td>{formatValue(entry.user_role)}</Td>
                  <Td>{actionMap[entry.action_type || ""] || formatValue(entry.action_type)}</Td>
                  <Td>
                    <div className="max-w-[240px] whitespace-normal text-slate-600">
                      {formatValue(entry.input_summary)}
                    </div>
                  </Td>
                  <Td>{formatValue(entry.document_code)}</Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </Panel>
  );
}

function SecurityPage({
  checks,
  loading,
  onRun,
}: {
  checks: SecurityCheckItem[];
  loading: boolean;
  onRun: () => Promise<void>;
}) {
  const passed = checks.filter((check) => check.ok).length;

  return (
    <div className="space-y-5">
      <Panel title="Kiểm tra bảo mật hệ thống">
        <p className="mb-4 text-sm text-muted-foreground">
          Kiểm tra tự động các điểm bảo mật theo yêu cầu GMP Data Integrity.
        </p>
        <Button disabled={loading} onClick={() => void onRun()} type="button">
          {loading ? "Đang kiểm tra..." : "Chạy kiểm tra bảo mật"}
        </Button>

        <div className="mt-4 space-y-2">
          {checks.length ? (
            <>
              <p className="font-semibold text-slate-900">
                Kết quả: {passed}/{checks.length} kiểm tra đạt
              </p>
              {checks.map((check) => (
                <div
                  key={check.label}
                  className={cn(
                    "flex items-start gap-3 border-b border-border/60 py-2 text-sm",
                    check.ok ? "text-emerald-700" : "text-rose-700",
                  )}
                >
                  <span className="text-base">{check.ok ? "✓" : "✗"}</span>
                  <div>
                    <strong>{check.label}</strong>
                    <span className="ml-2 text-slate-600">— {check.detail}</span>
                  </div>
                </div>
              ))}
            </>
          ) : (
            <StateBlock>Chưa chạy kiểm tra bảo mật.</StateBlock>
          )}
        </div>
      </Panel>

      <Panel title="Thông tin phiên bản">
        <p className="text-sm text-muted-foreground">
          GMP Validation Intelligence Dashboard — React parity build
        </p>
        <p className="mt-2 text-sm text-muted-foreground">
          Chỉ dùng nội bộ. Không phải hồ sơ GMP chính thức.
        </p>
        <p className="mt-2 text-sm text-muted-foreground">
          AI output cần người có chuyên môn xem xét trước khi dùng.
        </p>
      </Panel>

      <Panel title="Hợp đồng governance 4 tầng">
        <p className="mb-4 text-sm leading-6 text-muted-foreground">
          Bốn cổng được áp dụng nối tiếp. Frontend chỉ kiểm tra sớm; n8n và
          PostgreSQL là điểm thực thi có thẩm quyền.
        </p>
        <div className="space-y-3">
          {GOVERNANCE_LAYERS.map((layer, index) => (
            <details
              key={layer.id}
              className="group rounded-2xl border border-border bg-white px-4 py-3 shadow-sm"
              open={index === 0}
            >
              <summary className="cursor-pointer list-none font-semibold text-slate-900 marker:hidden">
                <span className="flex items-center justify-between gap-3">
                  {layer.title}
                  <span aria-hidden="true" className="text-primary group-open:rotate-45">
                    +
                  </span>
                </span>
              </summary>
              <div className="mt-3 space-y-2 border-t border-border/60 pt-3 text-sm leading-6">
                <p className="text-slate-700">{layer.gate}</p>
                <p className="text-muted-foreground">{layer.failure}</p>
              </div>
            </details>
          ))}
        </div>
        <Alert tone="info">
          Nội dung do AI tạo từ nguồn đã duyệt, cần người có chuyên môn xem xét
          trước khi dùng cho quyết định hoặc hồ sơ GMP chính thức.
        </Alert>
      </Panel>
    </div>
  );
}

function Snowfield() {
  const flakes = useMemo(
    () =>
      Array.from({ length: 28 }, (_, index) => ({
        left: `${(index * 11) % 100}%`,
        top: `${(index * 17) % 100}%`,
        delay: `${(index % 6) * 0.8}s`,
        duration: `${6 + (index % 7)}s`,
        size: `${8 + (index % 10)}px`,
        opacity: 0.16 + (index % 4) * 0.08,
      })),
    [],
  );

  return (
    <>
      {flakes.map((flake, index) => (
        <span
          key={index}
          className="absolute select-none text-white/70"
          style={{
            left: flake.left,
            top: flake.top,
            fontSize: flake.size,
            opacity: flake.opacity,
            animation: `snowfall ${flake.duration} linear infinite`,
            animationDelay: flake.delay,
          }}
        >
          ❄
        </span>
      ))}
    </>
  );
}

function Panel({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="overflow-hidden rounded-3xl border border-border/70 bg-white/80 shadow-[0_8px_30px_rgba(13,27,42,0.06)] backdrop-blur">
      <div className="border-b border-border/60 px-5 py-4">
        <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
          {title}
        </h3>
      </div>
      <div className="p-5">{children}</div>
    </section>
  );
}

function Alert({
  tone,
  children,
}: {
  tone: "danger" | "warning" | "info";
  children: ReactNode;
}) {
  const cls =
    tone === "danger"
      ? "border-rose-200 bg-rose-50 text-rose-800"
      : tone === "warning"
        ? "border-amber-200 bg-amber-50 text-amber-800"
        : "border-sky-200 bg-sky-50 text-sky-800";
  return <div className={cn("rounded-2xl border px-4 py-3 text-sm", cls)}>{children}</div>;
}

function StateBlock({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-dashed border-border bg-muted/30 px-4 py-6 text-center text-sm text-muted-foreground">
      {children}
    </div>
  );
}

function Button({
  children,
  className,
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary";
}) {
  const base =
    "inline-flex items-center justify-center rounded-2xl px-4 py-2.5 text-sm font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60";
  const variantClass =
    variant === "primary"
      ? "bg-primary text-primary-foreground hover:bg-primary/90"
      : "border border-border bg-white text-slate-800 hover:bg-slate-50";
  return (
    <button className={cn(base, variantClass, className)} {...props}>
      {children}
    </button>
  );
}

function Input({
  className,
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-11 w-full rounded-2xl border border-input bg-white px-4 text-sm text-slate-900 shadow-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/20",
        className,
      )}
      {...props}
    />
  );
}

function Select({
  className,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "h-11 w-full rounded-2xl border border-input bg-white px-4 text-sm text-slate-900 shadow-sm outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20",
        className,
      )}
      {...props}
    />
  );
}

function Badge({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-semibold",
        className,
      )}
    >
      {children}
    </span>
  );
}

function Pill({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold",
        className,
      )}
    >
      {children}
    </span>
  );
}

function StatCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone?: "success" | "warning" | "danger";
}) {
  const toneClass =
    tone === "success"
      ? "text-emerald-700"
      : tone === "warning"
        ? "text-amber-700"
        : tone === "danger"
          ? "text-rose-700"
          : "text-primary";
  return (
    <div className="rounded-2xl border border-border bg-white p-4 shadow-sm">
      <div className={cn("text-3xl font-semibold", toneClass)}>{value.toLocaleString("vi-VN")}</div>
      <div className="mt-1 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
        {label}
      </div>
    </div>
  );
}

function NavItem({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      className={cn(
        "flex w-full items-center gap-3 rounded-2xl px-4 py-3 text-left text-sm font-medium transition-colors",
        active
          ? "bg-white/12 text-white"
          : "text-white/70 hover:bg-white/8 hover:text-white",
      )}
      onClick={onClick}
      type="button"
    >
      {children}
    </button>
  );
}

function MobileNavItem({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      className={cn(
        "shrink-0 rounded-full border px-3 py-2 text-sm font-medium",
        active
          ? "border-primary/20 bg-primary/10 text-primary"
          : "border-border bg-white text-slate-700",
      )}
      onClick={onClick}
      type="button"
    >
      {children}
    </button>
  );
}

function Field({
  label,
  value,
  onChange,
  ...props
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
} & Omit<InputHTMLAttributes<HTMLInputElement>, "value" | "onChange">) {
  return (
    <label className="block space-y-2">
      <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-600">
        {label}
      </span>
      <Input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        {...props}
      />
    </label>
  );
}

function Th({ children }: { children: ReactNode }) {
  return <th className="px-4 py-3 font-semibold">{children}</th>;
}

function Td({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <td className={cn("px-4 py-3 align-top", className)}>{children}</td>;
}

function documentStatusClass(status: string): string {
  switch (status) {
    case "draft":
      return "bg-slate-100 text-slate-700";
    case "indexed":
      return "bg-primary/10 text-primary";
    case "reviewed":
      return "bg-amber-500/10 text-amber-700";
    case "approved_for_ai_use":
      return "bg-emerald-500/10 text-emerald-700";
    case "superseded":
      return "bg-rose-500/10 text-rose-700";
    default:
      return "bg-muted text-muted-foreground";
  }
}
