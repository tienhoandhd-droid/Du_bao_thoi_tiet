import { type FormEvent, useEffect, useRef, useState } from "react";
import { ApiError, fetchCopilotQuery } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { CopilotCitation } from "@/types/api";

const VALIDATION_TYPES = [
  { value: "iq", label: "IQ — Installation Qualification" },
  { value: "oq", label: "OQ — Operational Qualification" },
  { value: "pq", label: "PQ — Performance Qualification" },
];

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  grounded_pct?: number;
  citations?: CopilotCitation[];
}

export function CopilotPanel({
  token,
  onUnauthorized,
}: {
  token: string;
  onUnauthorized: () => void;
}) {
  const [equipmentCode, setEquipmentCode] = useState("");
  const [validationType, setValidationType] = useState("iq");
  const [query, setQuery] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!equipmentCode.trim()) {
      setError("Vui lòng nhập mã thiết bị.");
      return;
    }
    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      setError("Vui lòng nhập câu hỏi.");
      return;
    }
    setLoading(true);
    setError("");
    setMessages((prev) => [...prev, { role: "user", content: trimmedQuery }]);
    setQuery("");
    try {
      const data = await fetchCopilotQuery(
        {
          query: trimmedQuery,
          equipment_code: equipmentCode.trim(),
          validation_type: validationType,
          session_id: sessionId ?? undefined,
        },
        token,
      );
      if (data.session_id && !sessionId) {
        setSessionId(data.session_id);
      }
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer ?? "Không có câu trả lời.",
          grounded_pct: data.grounded_pct ?? 0,
          citations: data.citations ?? [],
        },
      ]);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        onUnauthorized();
        return;
      }
      setMessages((prev) => prev.slice(0, -1));
      setQuery(trimmedQuery);
      setError(err instanceof Error ? err.message : "Đã xảy ra lỗi không xác định.");
    } finally {
      setLoading(false);
    }
  }

  function resetSession() {
    setSessionId(null);
    setMessages([]);
    setError("");
  }

  return (
    <div className="space-y-5">
      <Panel title="Cấu hình phiên Copilot">
        <div className="grid gap-3 md:grid-cols-2">
          <FormField label="Mã thiết bị *">
            <Input
              placeholder="VD: HPLC-001"
              value={equipmentCode}
              onChange={(e) => setEquipmentCode(e.target.value)}
              maxLength={64}
              disabled={loading}
            />
          </FormField>
          <FormField label="Loại thẩm định *">
            <Select
              value={validationType}
              onChange={(e) => setValidationType(e.target.value)}
              disabled={loading}
            >
              {VALIDATION_TYPES.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </Select>
          </FormField>
        </div>
        {sessionId ? (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <p className="text-xs text-muted-foreground">
              Phiên:{" "}
              <span className="font-mono text-slate-700">
                {sessionId.slice(0, 8)}…
              </span>
            </p>
            <button
              type="button"
              onClick={resetSession}
              className="text-xs text-rose-600 hover:underline"
            >
              Kết thúc phiên
            </button>
          </div>
        ) : null}
      </Panel>

      {messages.length > 0 ? (
        <div className="space-y-4">
          {messages.map((msg, i) => (
            <MessageBubble key={i} message={msg} />
          ))}
          <div ref={bottomRef} />
        </div>
      ) : (
        <StateBlock>
          Nhập mã thiết bị và câu hỏi để bắt đầu phiên Validation Copilot. Copilot chỉ sử dụng SOP đã được phê duyệt.
        </StateBlock>
      )}

      {loading ? (
        <StateBlock>Copilot đang phân tích và truy xuất SOP đã duyệt, vui lòng đợi...</StateBlock>
      ) : null}

      <form onSubmit={(e) => void handleSubmit(e)} className="space-y-3">
        {error ? <Alert tone="danger">{error}</Alert> : null}
        <FormField label="Câu hỏi *">
          <textarea
            className="h-24 w-full resize-none rounded-2xl border border-input bg-white px-4 py-3 text-sm text-slate-900 shadow-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:bg-slate-50 disabled:text-muted-foreground"
            placeholder="VD: Hãy soạn tiêu chí chấp nhận cho bước Installation Verification của thiết bị này theo SOP hiện hành..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={loading}
          />
        </FormField>
        <Button type="submit" disabled={loading || !equipmentCode.trim()}>
          {loading ? "Đang xử lý..." : "Gửi câu hỏi"}
        </Button>
      </form>

      <Alert tone="warning">
        ⚕ Nội dung do AI tạo dựa trên SOP đã duyệt. Cần người có chuyên môn GMP xem xét và phê duyệt trước khi đưa vào hồ sơ chính thức.
      </Alert>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const [showCitations, setShowCitations] = useState(false);
  const isUser = message.role === "user";
  const hasCitations = (message.citations?.length ?? 0) > 0;
  const grounded_pct = message.grounded_pct ?? 0;
  const isGrounded = hasCitations && grounded_pct >= 80;

  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div className={cn("max-w-[85%] space-y-2", isUser ? "items-end" : "items-start")}>
        <div
          className={cn(
            "rounded-2xl px-4 py-3 text-sm leading-7",
            isUser
              ? "bg-primary text-primary-foreground"
              : "border border-border bg-white text-slate-800",
          )}
        >
          <div className="whitespace-pre-wrap">{message.content}</div>
        </div>

        {!isUser ? (
          <div className="flex flex-wrap items-center gap-2">
            {isGrounded ? (
              <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/20 bg-emerald-50 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-700">
                ✓ Có căn cứ SOP ({grounded_pct}%)
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 rounded-full border border-amber-500/20 bg-amber-50 px-2.5 py-0.5 text-[11px] font-semibold text-amber-700">
                ⚠ {hasCitations ? `Căn cứ thấp (${grounded_pct}%)` : "Chưa có căn cứ SOP"}
              </span>
            )}
            {hasCitations ? (
              <button
                type="button"
                onClick={() => setShowCitations((v) => !v)}
                className="text-xs text-primary hover:underline"
              >
                {showCitations
                  ? "Ẩn trích dẫn"
                  : `Xem ${message.citations!.length} trích dẫn`}
              </button>
            ) : null}
          </div>
        ) : null}

        {showCitations && hasCitations ? (
          <div className="overflow-x-auto rounded-2xl border border-border">
            <table className="min-w-full border-collapse text-[12px]">
              <thead className="bg-slate-50 text-left text-[11px] uppercase tracking-[0.14em] text-slate-500">
                <tr>
                  <th className="px-3 py-2 font-semibold">Tài liệu</th>
                  <th className="px-3 py-2 font-semibold">Đoạn trích dẫn</th>
                </tr>
              </thead>
              <tbody>
                {message.citations!.map((c) => (
                  <tr key={c.chunk_id} className="border-t border-border/60">
                    <td className="whitespace-nowrap px-3 py-2 align-top font-medium text-slate-800">
                      {c.document_code}
                    </td>
                    <td className="max-w-sm px-3 py-2 align-top leading-6 text-slate-600">
                      {c.text.length > 300 ? `${c.text.slice(0, 300)}…` : c.text}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function Panel({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
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
  children: React.ReactNode;
}) {
  const cls =
    tone === "danger"
      ? "border-rose-200 bg-rose-50 text-rose-800"
      : tone === "warning"
        ? "border-amber-200 bg-amber-50 text-amber-800"
        : "border-sky-200 bg-sky-50 text-sky-800";
  return (
    <div className={cn("rounded-2xl border px-4 py-3 text-sm", cls)}>
      {children}
    </div>
  );
}

function StateBlock({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-dashed border-border bg-muted/30 px-4 py-6 text-center text-sm text-muted-foreground">
      {children}
    </div>
  );
}

function Button({
  children,
  disabled,
  type,
}: {
  children: React.ReactNode;
  disabled?: boolean;
  type?: "submit" | "button";
}) {
  return (
    <button
      type={type ?? "button"}
      disabled={disabled}
      className="inline-flex items-center justify-center rounded-2xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
    >
      {children}
    </button>
  );
}

function Input({
  className,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-11 w-full rounded-2xl border border-input bg-white px-4 text-sm text-slate-900 shadow-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:bg-slate-50 disabled:text-muted-foreground",
        className,
      )}
      {...props}
    />
  );
}

function Select({
  children,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className="h-11 w-full rounded-2xl border border-input bg-white px-4 text-sm text-slate-900 shadow-sm outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:bg-slate-50 disabled:text-muted-foreground"
      {...props}
    >
      {children}
    </select>
  );
}

function FormField({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block space-y-2">
      <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-600">
        {label}
      </span>
      {children}
    </label>
  );
}
